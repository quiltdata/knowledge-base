# How do I clean up my Quilt stack's per-bucket Iceberg tables?

## Tags

`aws`, `athena`, `iceberg`, `lambda`, `sqs`, `tabulator`, `performance`, `cost`, `maintenance`

## Summary

Since Quilt 1.70.0, every stack keeps four Apache Iceberg tables per bucket (`<bucket>_package_revision`, `<bucket>_package_tag`, `<bucket>_package_manifest` and `<bucket>_package_entry`), which Tabulator and Athena queries read. Nothing compacts these tables or expires their old snapshots, so they grow with every package push and every stack update. On a busy stack, the Lambda that writes them eventually runs past its timeout. Package events then go to the Lambda's dead-letter queue and expire there, so those packages are missing from the tables. This article shows how to check how urgently your stack needs a cleanup, and how to run a one-time cleanup with a script.

---

## Who needs this

Every stack on Quilt 1.70.0 or later has these tables, and none of them is ever compacted, so every such stack benefits from one cleanup. Quilt 26.11.0 deprecates the per-bucket tables in favor of [stack-wide package tables](https://docs.quilt.bio/quilt-platform/advanced/iceberg-tables#stack-wide-package-tables), which it compacts on a schedule. However, 26.11.0 still writes and reads the per-bucket tables, so a stack on 26.11.0 needs the cleanup too. The check in Step 2 tells you whether to run it now or at a convenient time.

## Symptoms

- The stack's Iceberg Lambda (`<stack>-IcebergLambda-<suffix>`) runs close to or into its 60-second timeout, or logs `ICEBERG_COMMIT_ERROR`.
- Messages appear in its dead-letter queue (`<stack>-IcebergLambdaDeadLetterQueue-<suffix>`).
- Athena queries on the `<bucket>_package_*` tables get slower, and Tabulator results do not include recently pushed packages.
- The stack's Iceberg bucket (`<stack>-icebergbucket-<suffix>`) keeps growing, with a rising S3 request cost.

## What the cleanup does

1. Pauses the Iceberg Lambda, which the script's output calls *the writer*. It disables the Lambda's SQS trigger (an event source mapping; in the Lambda console, the function's **Configuration → Triggers**) and waits for work already in progress to finish. Package events wait in the Lambda's queue meanwhile.
2. For every per-bucket table: sets a short snapshot retention, runs `VACUUM` and `OPTIMIZE` to drop old snapshots and compact the data files, reloads the table from the bucket's package pointers and manifests (the same statements a stack update runs), compacts again, and removes the short retention.
3. Re-enables the Lambda, which then processes the queued events.

The old snapshots are removed permanently: queries on these tables with `FOR VERSION AS OF` or `FOR TIMESTAMP AS OF` can no longer reach them.

The reload restores rows for packages whose events were lost. If a package was deleted and the event for that deletion was lost, the reload does not remove the package's rows. The reload also skips the following, and their rows stay as the Lambda wrote them:

- packages whose namespace or name begins with `_` or `.` (Athena does not read these);
- files under `.quilt/packages/` whose name is not a 64-character hash.

The tables start to grow again after the cleanup. If your stack stays on its current release for months, rerun the check (Step 2) monthly.

---

## Before you start

- **Duration.** It grows with the number of buckets and how heavily they are used. On a test stack with 4 lightly used buckets it took 6 minutes; on an internal stack with 13 buckets and tables of up to 3,600 snapshots, 25 minutes. On Quilt's most heavily loaded internal stack (71 buckets, tables with up to 18,000 snapshots), compacting the tables alone took 49 minutes, 16 tables at a time; the script also reloads every table and works on 4 at a time by default, so expect longer on a stack like that. Package events are not indexed into these tables until it finishes; they are not lost unless the pause lasts days (the queue keeps a message 4 days).
- **No stack update, manual trigger change or `abort` while it runs.** A stack update can reload these tables and would conflict with the cleanup. Before you start, pause any CI job or scheduled deployment that updates the stack. If an update starts anyway, the script starts no new statements, but a statement already running still finishes. For the same reason, while the script runs, do not re-enable the Lambda's trigger by hand, and do not start `abort` on this or any other machine. To abort, stop the script with Ctrl-C, wait for it to exit, and then run `abort` (see **If the run is interrupted**).
- **Where to run it.** Any shell with [uv](https://docs.astral.sh/uv/) and AWS credentials for the stack's account; uv downloads the script for each command and installs what it needs (Python 3.9 or later and `boto3`). Whatever stops the script midway, such as a closed session or expired credentials, leaves the Lambda paused (see **If the run is interrupted** below). The script keeps its progress in a file on the machine that runs it, and in CloudShell each region counts as a separate machine. `run` started on another machine begins the cleanup again from the start, which is safe; `abort` works from any machine.
  - **AWS CloudShell** [ends a session after 20–30 minutes without keyboard or pointer input](https://docs.aws.amazon.com/cloudshell/latest/userguide/limits.html) (10 in GovCloud); a running command does not count as input. During a run, click inside the tab at least every 15 minutes (every 5 in GovCloud).
  - **Your own machine** (a laptop, a bastion host) has no such timeout. Keep it awake, and use credentials that outlast the run or refresh themselves, such as a profile you sign in to with `aws sso login`.
- **Credentials.** Use a role that can update the stack, such as the one you deploy it with. The script reads the stack's resources, CloudWatch metrics and the Iceberg Lambda's queues, and updates the Lambda's event source mapping. It also runs Athena statements in the stack's Iceberg workgroup; these statements read the buckets' `.quilt/` objects and rewrite the Iceberg bucket.
  - The role needs `s3:DeleteObject` on the Iceberg bucket. Without it, `VACUUM` succeeds but deletes no files.
  - The script has not been tested on a stack that enforces Lake Formation (`EnableLakeFormationGrants` is `Enabled`). On such a stack, the role also needs Lake Formation permissions to alter, read and write the tables in the stack's Iceberg database (its `IcebergDatabase` resource) and to read the tables in its user Athena database (its `UserAthenaDatabase` resource). If the script reports access errors on such a stack, contact Quilt support.

## Step 1 — Install uv and read the script

[Install uv](https://docs.astral.sh/uv/getting-started/installation/).

The commands below run the script straight from this article's repository at a fixed commit, so every command runs the same code. Read it there before you run it: [quilt_iceberg_cleanup.py](https://github.com/quiltdata/knowledge-base/blob/__COMMIT__/howto-clean-up-per-bucket-iceberg-tables/quilt_iceberg_cleanup.py). Each command prints the script's version first.

## Step 2 — Check how urgent it is

The check only reads. Use your Quilt stack's own CloudFormation name (not a parent stack's) and its region:

```bash
uv run https://raw.githubusercontent.com/quiltdata/knowledge-base/__COMMIT__/howto-clean-up-per-bucket-iceberg-tables/quilt_iceberg_cleanup.py \
  check --stack <STACK_NAME> --region <REGION>
```

It prints:

- a daily table for the last 14 days with the Iceberg Lambda's longest run, its error count and the most messages its dead-letter queue held;
- the number of days on which the Lambda reached its timeout, the number of messages in the dead-letter queue now, and the Iceberg bucket's size (write the size down for Step 4);
- a verdict:
  - **Run the cleanup now** if the Lambda reached its timeout or the dead-letter queue held any message: package events are being lost.
  - **Run it at a convenient time** otherwise, preferably before your next stack update, since each update adds to the tables.

Even when the check finds no timeouts and no dead-lettered messages, some rows may be missing. Before Quilt 26.9.0, when two writes conflicted, one of them was dropped silently. The cleanup's reload restores those rows too.

## Step 3 — Run the cleanup

```bash
uv run https://raw.githubusercontent.com/quiltdata/knowledge-base/__COMMIT__/howto-clean-up-per-bucket-iceberg-tables/quilt_iceberg_cleanup.py \
  run --stack <STACK_NAME> --region <REGION>
```

It prints how many tables and buckets it found and lists the buckets it can compact but not reload, because their source tables (`<bucket>_packages` and `<bucket>_manifests` in the stack's user Athena database) are missing or unreadable. Then it asks you to type `yes`, pauses the Lambda and prints the cleanup's progress. `--workers N` sets how many tables it works on at a time (default 4); raise it if your account's Athena DML concurrency quota allows.

The script stops early if the Lambda's event source mapping is re-enabled, a stack update starts, another statement writes the tables, or an unexpected error occurs. It then starts no new statements, waits for the running ones to finish and prints `STOPPED`. Then follow **If the run is interrupted**.

If some tables fail with an Athena error, the script still finishes the other tables. It then removes the short retention from the failed tables (or says that it could not), re-enables the Lambda and lists the failed tables. A later `run` retries them.

## Step 4 — Afterwards

When it prints `Done`, the Lambda is enabled again and works through its queue; watch the queue (`<stack>-IcebergLambdaQueue-<suffix>`) drain in the SQS console. Resume any CI job or scheduled deployment that you paused.

Five days later, run the check again with `--since` set to the day after the cleanup (a date in UTC):

```bash
uv run https://raw.githubusercontent.com/quiltdata/knowledge-base/__COMMIT__/howto-clean-up-per-bucket-iceberg-tables/quilt_iceberg_cleanup.py \
  check --stack <STACK_NAME> --region <REGION> --since <YYYY-MM-DD>
```

It should print `Days at the timeout: 0. Dead-letter queue now: 0 messages.` (messages dead-lettered before the cleanup expire within 4 days), and the Iceberg bucket's size should be smaller than the size you wrote down in Step 2 (the size is measured once a day).

## If the run is interrupted

If the script stops early (for example, after an error, a closed session or Ctrl-C), it **leaves the Lambda paused** and keeps its progress in `~/.quilt-iceberg-cleanup/<STACK_NAME>.json`. The check (Step 2) also reports a paused Lambda. To recover, do one of the following:

- run `run` again to finish the cleanup, or
- give up with `abort`, which waits for statements still running, removes the short retention from every table and re-enables the Lambda:

```bash
uv run https://raw.githubusercontent.com/quiltdata/knowledge-base/__COMMIT__/howto-clean-up-per-bucket-iceberg-tables/quilt_iceberg_cleanup.py \
  abort --stack <STACK_NAME> --region <REGION>
```

After `abort`, resume any CI job or scheduled deployment that you paused.

Do not leave the Lambda paused for days: its queue drops a message 4 days after it arrives. If neither `run` nor `abort` can finish (for example, because the role lacks a permission they need), you can re-enable the Lambda's SQS trigger by hand. Before you do, make sure that:

1. the script is not running; and
2. Athena's **Recent queries** for the stack's Iceberg workgroup (its `IcebergWorkGroup` resource in CloudFormation) show no running statement on the `<bucket>_package_*` tables.

Then re-enable the trigger in the Lambda console (the function's **Configuration → Triggers**). The tables keep the cleanup's short retention until a later `run` or `abort` finishes.

If the cleanup reports tables it could not finish, or anything else looks wrong, [contact Quilt support](mailto:support@quilt.bio) with the script's output.
