#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["boto3"]
# ///
"""Clean up a Quilt stack's per-bucket Iceberg tables (<bucket>_package_revision,
_package_tag, _package_manifest, _package_entry).

  uv run quilt_iceberg_cleanup.py check --stack STACK   # read-only: how soon to run the cleanup
  uv run quilt_iceberg_cleanup.py run   --stack STACK   # the cleanup; rerun to resume after an interruption
  uv run quilt_iceberg_cleanup.py abort --stack STACK   # give up: unset the cleanup's table properties, re-enable the writer

The cleanup pauses the Lambda that writes these tables (its SQS event source mapping; package
events wait in its queue), then for every table: sets short snapshot retention, VACUUM, OPTIMIZE,
VACUUM, reloads the table from the bucket's package pointers and manifests (the same MERGE a stack
deploy runs), OPTIMIZE, waits out the retention age, VACUUM, and unsets the properties. Finally it
re-enables the writer, which then processes the queued events.

Needs Python 3.9+ and boto3 (`uv run` installs both, from the header above), and credentials
allowed to manage the stack's Iceberg tables (see the accompanying article). Progress is kept in ~/.quilt-iceberg-cleanup/<stack>.json.
"""

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import re
import sys
import threading
import time
from pathlib import Path

import boto3

VERSION = "2026-11-18"
TABLE_RE = re.compile(r"^(?P<bucket>.+)_package_(?P<kind>revision|tag|manifest|entry)$")
WRITE_RE = re.compile(r"^\s*(MERGE|INSERT|DELETE|UPDATE|ALTER|OPTIMIZE|VACUUM)\b", re.I)
SET_PROPS = ("('vacuum_max_snapshot_age_seconds'='60', 'vacuum_min_snapshots_to_keep'='1', "
             "'optimize_rewrite_delete_file_threshold'='1')")
UNSET_PROPS = ("('vacuum_max_snapshot_age_seconds', 'vacuum_min_snapshots_to_keep', "
               "'optimize_rewrite_delete_file_threshold')")
RETENTION_WAIT = 65  # seconds: the 60 s retention age plus a margin
CHECK_DAYS = 14
# Per-table phases, in order. "load" is skipped for a bucket whose source tables cannot be read.
PHASES = ["alter", "vacuum1", "optimize1", "vacuum2", "load", "optimize2", "vacuum3", "unset", "done"]


def now():
    return dt.datetime.now(dt.timezone.utc)


def say(*a):
    print(f"[{now():%H:%M:%S}]", *a, flush=True)


def ident(name):
    return '"' + name.replace('"', '""') + '"'


class Stack:
    """The stack's resources that the cleanup touches, found by their logical IDs."""

    def __init__(self, name, region):
        self.session = boto3.Session(region_name=region)
        c = self.session.client
        self.cfn, self.lam, self.sqs, self.cw, self.glue, self.ath = (
            c("cloudformation"), c("lambda"), c("sqs"), c("cloudwatch"), c("glue"), c("athena"))
        self.name = name
        self.stack_id = self.cfn.describe_stacks(StackName=name)["Stacks"][0]["StackId"]
        res = {}
        for page in self.cfn.get_paginator("list_stack_resources").paginate(StackName=name):
            for r in page["StackResourceSummaries"]:
                res[r["LogicalResourceId"]] = r.get("PhysicalResourceId")
        need = ["IcebergLambda", "IcebergLambdaEventSourceMapping", "IcebergLambdaQueue",
                "IcebergLambdaDeadLetterQueue", "IcebergWorkGroup", "IcebergDatabase", "UserAthenaDatabase"]
        missing = [n for n in need if not res.get(n)]
        if missing:
            sys.exit(f"Stack {name} has no {', '.join(missing)}: it is not a Quilt stack on 1.70.0 or later, "
                     "or it is a parent stack (pass the Quilt stack's own name).")
        self.function = res["IcebergLambda"]
        self.esm = res["IcebergLambdaEventSourceMapping"]
        self.queue = res["IcebergLambdaQueue"]
        self.dlq = res["IcebergLambdaDeadLetterQueue"]
        self.workgroup = res["IcebergWorkGroup"]
        self.db = res["IcebergDatabase"]
        self.user_db = res["UserAthenaDatabase"]
        self.bucket = res.get("IcebergBucket")

    def status(self):
        return self.cfn.describe_stacks(StackName=self.name)["Stacks"][0]["StackStatus"]

    def mapping_state(self):
        return self.lam.get_event_source_mapping(UUID=self.esm)["State"]

    def set_mapping(self, enabled):
        self.lam.update_event_source_mapping(UUID=self.esm, Enabled=enabled)
        want = "Enabled" if enabled else "Disabled"
        for _ in range(60):
            if self.mapping_state() == want:
                return
            time.sleep(5)
        raise RuntimeError(f"the writer's event source mapping did not reach {want}")

    def in_flight(self):
        a = self.sqs.get_queue_attributes(QueueUrl=self.queue, AttributeNames=[
            "ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"])["Attributes"]
        return int(a["ApproximateNumberOfMessages"]), int(a["ApproximateNumberOfMessagesNotVisible"])

    def tables(self):
        names = []
        for page in self.glue.get_paginator("get_tables").paginate(DatabaseName=self.db):
            names += [t["Name"] for t in page["TableList"] if TABLE_RE.match(t["Name"])]
        return sorted(names)

    def user_tables(self):
        names = set()
        for page in self.glue.get_paginator("get_tables").paginate(DatabaseName=self.user_db):
            names.update(t["Name"] for t in page["TableList"])
        return names


class Athena:
    """Runs statements in the stack's Iceberg workgroup and remembers which ones are ours."""

    def __init__(self, stack):
        self.s = stack
        self.ours = set()
        self.lock = threading.Lock()

    def run(self, sql):
        """Returns (state, reason, query id)."""
        for attempt in range(8):
            try:
                qid = self.s.ath.start_query_execution(
                    QueryString=sql, QueryExecutionContext={"Database": self.s.db},
                    WorkGroup=self.s.workgroup)["QueryExecutionId"]
                break
            except self.s.ath.exceptions.TooManyRequestsException:
                time.sleep(5 * (attempt + 1))
        else:
            raise RuntimeError("Athena refused to start the statement 8 times (too many requests)")
        with self.lock:
            self.ours.add(qid)
        while True:
            q = self.s.ath.get_query_execution(QueryExecutionId=qid)["QueryExecution"]
            state = q["Status"]["State"]
            if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
                return state, q["Status"].get("StateChangeReason", ""), qid
            time.sleep(3)

    def rows(self, sql):
        state, reason, qid = self.run(sql)
        if state != "SUCCEEDED":
            raise RuntimeError(f"{state}: {reason}")
        out = self.s.ath.get_query_results(QueryExecutionId=qid)["ResultSet"]["Rows"]
        return [[c.get("VarCharValue") for c in r["Data"]] for r in out[1:]]

    def foreign_writes(self, tables, minutes=60):
        """Queued or running writes to these tables that this script did not start."""
        cutoff = now() - dt.timedelta(minutes=minutes)
        found = []
        for page in self.s.ath.get_paginator("list_query_executions").paginate(WorkGroup=self.s.workgroup):
            ids, older = page["QueryExecutionIds"], False
            for i in range(0, len(ids), 50):
                for q in self.s.ath.batch_get_query_execution(QueryExecutionIds=ids[i:i + 50])["QueryExecutions"]:
                    if q["Status"]["SubmissionDateTime"] < cutoff:
                        older = True
                        continue
                    if q["Status"]["State"] not in ("QUEUED", "RUNNING"):
                        continue
                    with self.lock:
                        if q["QueryExecutionId"] in self.ours:
                            continue
                    text = q["Query"]
                    if WRITE_RE.match(text) and any(t in text for t in tables):
                        found.append(q["QueryExecutionId"])
            if older:
                break
        return found


# ---------- check ----------

def metric(cw, namespace, name, dims, stat, start, end):
    pts = cw.get_metric_statistics(Namespace=namespace, MetricName=name, Dimensions=dims,
                                   StartTime=start, EndTime=end, Period=86400, Statistics=[stat])["Datapoints"]
    return sorted(((p["Timestamp"].date(), p[stat]) for p in pts))


def check(args):
    s = Stack(args.stack, args.region)
    end = dt.datetime.combine(args.until, dt.time(), dt.timezone.utc) if args.until else now()
    since = dt.datetime.combine(args.since, dt.time(), dt.timezone.utc) if args.since else None
    start = since or end - dt.timedelta(days=CHECK_DAYS)
    timeout = s.lam.get_function_configuration(FunctionName=s.function)["Timeout"]
    fdim = [{"Name": "FunctionName", "Value": s.function}]
    duration = {d: v / 1000 for d, v in metric(s.cw, "AWS/Lambda", "Duration", fdim, "Maximum", start, end)}
    errors = dict(metric(s.cw, "AWS/Lambda", "Errors", fdim, "Sum", start, end))
    dlq_name = s.dlq.rsplit("/", 1)[1]
    dlq = dict(metric(s.cw, "AWS/SQS", "ApproximateNumberOfMessagesVisible",
                      [{"Name": "QueueName", "Value": dlq_name}], "Maximum", start, end))
    dlq_now = int(s.sqs.get_queue_attributes(QueueUrl=s.dlq, AttributeNames=["ApproximateNumberOfMessages"])
                  ["Attributes"]["ApproximateNumberOfMessages"])
    tables = s.tables()

    timed_out = [d for d, v in duration.items() if v >= timeout * 0.98]
    dlq_max = max(dlq.values(), default=0)
    print(f"Stack {s.name}: {len(tables)} per-bucket tables in {s.db}")
    print(f"Writer {s.function}: timeout {timeout} s")
    print(f"Window: {start:%Y-%m-%d} to {end:%Y-%m-%d} (UTC)")
    print("\nDay (UTC)   longest run  errors  dead-letter queue (most messages)")
    for d in sorted(set(duration) | set(errors) | set(dlq)):
        def cell(m, fmt):
            return fmt.format(m[d]) if d in m else "-"
        print(f"{d}  {cell(duration, '{:.0f} s'):>11}  {cell(errors, '{:.0f}'):>6}  {cell(dlq, '{:.0f}'):>8}")
    print(f"\nDays at the timeout: {len(timed_out)}. Dead-letter queue now: {dlq_now} messages.")
    settled = False
    if since:
        # A message dead-lettered before `since` stays until 4 days after it was first queued.
        settled = end - since >= dt.timedelta(days=4)
        dlq_bad = settled and dlq_now > 0
        if not settled:
            print(f"Messages dead-lettered before {since:%Y-%m-%d} can stay until "
                  f"{since + dt.timedelta(days=4):%Y-%m-%d}; until then the verdict leaves the dead-letter "
                  "queue out.")
    else:
        dlq_bad = dlq_max > 0
    if s.bucket:
        size = metric(s.cw, "AWS/S3", "BucketSizeBytes",
                      [{"Name": "BucketName", "Value": s.bucket}, {"Name": "StorageType", "Value": "StandardStorage"}],
                      "Average", end - dt.timedelta(days=3), end)
        if size:
            print(f"Iceberg bucket {s.bucket}: {size[-1][1] / 1e9:.1f} GB")
    state = s.mapping_state()
    if state != "Enabled":
        print(f"\nThe writer's event source mapping is {state}: package events are waiting in its queue, "
              "which drops a message 4 days after it arrives.")
        mine = load_state(s.name)
        if mine.get("tables") and mine.get("stack_id") in (None, s.stack_id):
            print("A cleanup started from this machine is unfinished.")
        print("\nVerdict: THE WRITER IS PAUSED. Finish the cleanup with `run`, or give it up with `abort`, "
              "which resumes the writer.")
    elif since and not (timed_out or dlq_bad):
        print(f"\nVerdict: no timeouts since {since:%Y-%m-%d}"
              + (" and no dead-lettered events." if settled else "."))
    elif timed_out or dlq_bad:
        print("\nVerdict: RUN THE CLEANUP NOW. The writer is hitting its timeout or failing events into its "
              "dead-letter queue, where they expire: package rows are being lost.")
    else:
        print("\nVerdict: run the cleanup at a convenient time, preferably before the stack's next update. "
              "No timeouts or dead-lettered events in the window, but the tables still grow with every "
              "push and every stack update.")


# ---------- run / abort ----------

def state_path(stack):
    return Path.home() / ".quilt-iceberg-cleanup" / f"{stack}.json"


def load_state(stack):
    p = state_path(stack)
    return json.loads(p.read_text()) if p.exists() else {}


class Progress:
    def __init__(self, stack):
        self.path = state_path(stack)
        self.path.parent.mkdir(exist_ok=True)
        self.data = load_state(stack)
        self.lock = threading.Lock()

    def save(self):
        with self.lock:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, indent=1, sort_keys=True))
            tmp.replace(self.path)

    def phase(self, table):
        return self.data["tables"].get(table, "alter")

    def set_phase(self, table, phase):
        with self.lock:
            self.data["tables"][table] = phase
        self.save()


def bulk_load(user_db, table):
    m = TABLE_RE.match(table)
    bucket, kind = m["bucket"], m["kind"]
    packages = f"{ident(user_db)}.{ident(bucket + '_packages')}"
    manifests = f"{ident(user_db)}.{ident(bucket + '_manifests')}"
    t = ident(table)
    pkg_name = "regexp_extract(\"$path\", '^s3://[^/]+/[^/]+/[^/]+/([^/]+/[^/]+)', 1)"
    pointer = "regexp_extract(\"$path\", '[^/]+$')"
    top_hash = "regexp_extract(\"$path\", '[^/]+$')"
    is_manifest = "regexp_like(\"$path\", '/[a-z0-9]{64}$')"
    if kind == "revision":
        return f"""MERGE INTO {t} AS t USING (
            SELECT {pkg_name} AS pkg_name, from_unixtime(CAST({pointer} AS bigint)) AS timestamp, top_hash
            FROM {packages} WHERE TRY_CAST({pointer} AS bigint) IS NOT NULL) AS s
            ON t.pkg_name = s.pkg_name AND t.timestamp = s.timestamp
            WHEN MATCHED THEN UPDATE SET top_hash = s.top_hash
            WHEN NOT MATCHED THEN INSERT (pkg_name, timestamp, top_hash) VALUES (s.pkg_name, s.timestamp, s.top_hash)"""
    if kind == "tag":
        return f"""MERGE INTO {t} AS t USING (
            SELECT {pkg_name} AS pkg_name, {pointer} AS tag_name, top_hash
            FROM {packages} WHERE TRY_CAST({pointer} AS bigint) IS NULL) AS s
            ON t.pkg_name = s.pkg_name AND t.tag_name = s.tag_name
            WHEN MATCHED THEN UPDATE SET top_hash = s.top_hash
            WHEN NOT MATCHED THEN INSERT (pkg_name, tag_name, top_hash) VALUES (s.pkg_name, s.tag_name, s.top_hash)"""
    if kind == "manifest":
        return f"""MERGE INTO {t} AS t USING (
            SELECT {top_hash} AS top_hash, message, user_meta AS metadata
            FROM {manifests} WHERE logical_key IS NULL AND {is_manifest}) AS s
            ON t.top_hash = s.top_hash
            WHEN MATCHED THEN UPDATE SET message = s.message, metadata = s.metadata
            WHEN NOT MATCHED THEN INSERT (top_hash, message, metadata) VALUES (s.top_hash, s.message, s.metadata)"""
    return f"""MERGE INTO {t} AS t USING (
        SELECT {top_hash} AS top_hash, logical_key, physical_keys[1] AS physical_key, hash.type AS hash_type,
            hash.value AS hash_value, size, meta AS metadata
        FROM {manifests} WHERE logical_key IS NOT NULL AND {is_manifest}) AS s
        ON t.top_hash = s.top_hash AND t.logical_key = s.logical_key
        WHEN MATCHED THEN UPDATE SET physical_key = s.physical_key, hash_type = s.hash_type,
            hash_value = s.hash_value, size = s.size, metadata = s.metadata
        WHEN NOT MATCHED THEN INSERT (top_hash, logical_key, physical_key, hash_type, hash_value, size, metadata)
            VALUES (s.top_hash, s.logical_key, s.physical_key, s.hash_type, s.hash_value, s.size, s.metadata)"""


class Cleanup:
    def __init__(self, args):
        self.args = args
        self.s = Stack(args.stack, args.region)
        self.a = Athena(self.s)
        self.p = Progress(args.stack)
        other = self.p.data.get("stack_id")
        if other and other != self.s.stack_id:
            sys.exit(f"{self.p.path} belongs to another stack named {args.stack} ({other}). "
                     "Move it away, then rerun.")
        self.paused_here = False  # whether this run disabled the writer's mapping
        self.stop = threading.Event()
        self.guard_off = threading.Event()  # set before the cleanup itself re-enables the writer
        self.stop_reason = []
        self.failed = {}
        self.check_lock = threading.Lock()
        self.checked_at = 0.0

    # -- guard: stop starting statements if anything else could write these tables --
    def halt(self, reason):
        if not self.stop.is_set():
            self.stop_reason.append(reason)
            say(f"STOPPING: {reason}. Statements already running finish; no new ones start.")
            self.stop.set()

    def fast_hazard(self):
        st = self.s.mapping_state()
        if st != "Disabled":
            return f"the writer's event source mapping is {st}"
        status = self.s.status()
        if status.endswith("IN_PROGRESS"):
            return f"the stack is {status} (a stack update reloads these tables)"
        return None

    def clear(self):
        """Checked right before each statement starts; the workers share a result for 2 s."""
        with self.check_lock:
            if self.stop.is_set():
                return False
            if time.time() - self.checked_at > 2:
                try:
                    bad = self.fast_hazard()
                except Exception as e:  # a failed check is not a pass
                    bad = f"the safety check failed: {e!r}"
                if bad:
                    self.halt(bad)
                    return False
                self.checked_at = time.time()
            return True

    def guard(self, tables):
        """Polls what is too slow to check before every statement: other statements writing the tables."""
        while not self.stop.is_set() and not self.guard_off.is_set():
            try:
                bad = self.fast_hazard()
                if not bad:
                    foreign = self.a.foreign_writes(tables)
                    bad = foreign and f"another statement is writing these tables: {foreign[:3]}"
            except Exception as e:  # a failed check is not a pass
                bad = f"the safety check failed: {e!r}"
            if bad and not self.guard_off.is_set():
                self.halt(bad)
                return
            self.guard_off.wait(30)

    def until_done(self, table, label, sql, marker):
        runs = fails = 0
        while self.clear():
            state, reason, qid = self.a.run(sql)
            runs += 1
            if state == "SUCCEEDED" and marker not in reason:
                return True
            if marker in reason:
                if runs % 5 == 0:
                    say(f"  {table}: {label} needs more runs ({runs} so far)")
                if runs >= 300:
                    break
                continue
            fails += 1
            say(f"  {table}: {label} {state}: {reason[:300]}")
            if fails >= 3:
                break
            time.sleep(10)
        self.failed.setdefault(table, f"{label} did not finish")
        return False

    def table_pipeline(self, table, loadable, upto):
        t = f"`{table}`"
        steps = {
            "alter": lambda: self.once(table, "ALTER", f"ALTER TABLE {t} SET TBLPROPERTIES {SET_PROPS}"),
            "vacuum1": lambda: self.until_done(table, "VACUUM", f"VACUUM {t}", "ICEBERG_VACUUM_MORE_RUNS_NEEDED"),
            "optimize1": lambda: self.until_done(table, "OPTIMIZE", f"OPTIMIZE {t} REWRITE DATA USING BIN_PACK",
                                                 "ICEBERG_OPTIMIZE_MORE_RUNS_NEEDED"),
            "vacuum2": lambda: self.until_done(table, "VACUUM", f"VACUUM {t}", "ICEBERG_VACUUM_MORE_RUNS_NEEDED"),
            "load": lambda: self.load(table, loadable),
            "optimize2": lambda: self.until_done(table, "OPTIMIZE", f"OPTIMIZE {t} REWRITE DATA USING BIN_PACK",
                                                 "ICEBERG_OPTIMIZE_MORE_RUNS_NEEDED"),
            "vacuum3": lambda: self.until_done(table, "VACUUM", f"VACUUM {t}", "ICEBERG_VACUUM_MORE_RUNS_NEEDED"),
            "unset": lambda: self.unset(table),
        }
        while True:
            phase = self.p.phase(table)
            if phase == upto or phase == "done" or self.stop.is_set():
                return
            if not steps[phase]():
                return
            nxt = PHASES[PHASES.index(phase) + 1]
            self.p.set_phase(table, nxt)
            if nxt == "done":
                say(f"  {table}: done")

    def once(self, table, label, sql, gated=True):
        for attempt in range(3):
            if not (self.clear() if gated else not self.stop.is_set()):
                return False
            state, reason, qid = self.a.run(sql)
            if state == "SUCCEEDED":
                return True
            say(f"  {table}: {label} {state}: {reason[:300]}")
            time.sleep(10)
        self.failed.setdefault(table, f"{label} failed")
        return False

    def load(self, table, loadable):
        bucket = TABLE_RE.match(table)["bucket"]
        if bucket not in loadable:
            return True  # no readable source tables for this bucket; nothing to reload from
        return self.once(table, "reload", bulk_load(self.s.user_db, table))

    def unset(self, table):
        # A rerun after an interruption may find the properties already unset.
        sql = f"ALTER TABLE `{table}` UNSET TBLPROPERTIES {UNSET_PROPS}"
        state, reason, _ = self.a.run(sql)
        if state == "SUCCEEDED" or re.search(r"not (exist|found)", reason, re.I):
            return True
        say(f"  {table}: UNSET {state}: {reason[:300]}")
        return self.once(table, "UNSET", sql, gated=False)

    def run_pass(self, tables, loadable, upto):
        ex = cf.ThreadPoolExecutor(self.args.workers)
        futures = [ex.submit(self.table_pipeline, t, loadable, upto) for t in tables]
        try:
            for f in cf.as_completed(futures):
                if f.exception():
                    # Its statement may still be running, so the writer must not resume yet.
                    self.halt(f"an unexpected error: {f.exception()!r}")
        except KeyboardInterrupt:
            # Set the stop before waiting for the workers, so queued tables start nothing.
            self.interrupted()
            ex.shutdown(wait=True)
            raise
        ex.shutdown(wait=True)

    def interrupted(self):
        if not self.stop.is_set():
            self.stop.set()
            say("Interrupted: stopping once the running statements finish.")

    def preflight(self):
        try:
            return self._preflight()
        except Exception as e:
            sys.exit(f"Stopped before changing anything: {e!r}")

    def _preflight(self):
        status = self.s.status()
        if status.endswith("IN_PROGRESS"):
            sys.exit(f"The stack is {status}. Run the cleanup when no stack update is in progress.")
        tables = self.p.data.get("tables") and sorted(self.p.data["tables"]) or self.s.tables()
        if not tables:
            sys.exit(f"No per-bucket tables in {self.s.db}; nothing to clean up.")
        # Calls the run makes once the writer is paused; a missing permission must show up now.
        self.s.mapping_state()
        self.s.in_flight()
        self.a.foreign_writes(tables)
        user = self.s.user_tables()
        buckets = sorted({TABLE_RE.match(t)["bucket"] for t in tables})
        loadable, skipped = [], []
        say(f"Checking read access to the source tables of {len(buckets)} buckets ...")
        for b in buckets:
            if f"{b}_packages" not in user or f"{b}_manifests" not in user:
                skipped.append(f"{b} (no source tables)")
                continue
            try:
                for src in ("packages", "manifests"):
                    self.a.rows(f"SELECT 1 FROM {ident(self.s.user_db)}.{ident(b + '_' + src)} LIMIT 1")
                loadable.append(b)
            except RuntimeError as e:
                skipped.append(f"{b} ({str(e)[:120]})")
        self.a.rows(f'SELECT count(*) FROM {ident(tables[0] + "$snapshots")}')
        return tables, loadable, skipped

    def run(self):
        tables, loadable, skipped = self.preflight()
        print(f"\nStack {self.s.name}: {len(tables)} per-bucket tables in {len(set(TABLE_RE.match(t)['bucket'] for t in tables))} buckets.")
        if skipped:
            print("Tables of these buckets are compacted but not reloaded:\n  " + "\n  ".join(skipped))
        if not self.p.data.get("tables"):
            print("\nThe cleanup pauses the writer Lambda's event source mapping until it finishes; "
                  "package events wait in its queue meanwhile (they expire after 4 days).")
            if not self.args.yes and input("Type 'yes' to start: ").strip() != "yes":
                sys.exit("Not started.")
            self.p.data = {"started": now().isoformat(), "stack_id": self.s.stack_id,
                           "tables": {t: "alter" for t in tables}}
            self.p.save()
        else:
            print(f"Resuming the cleanup started {self.p.data.get('started')}.")

        try:
            if self.s.mapping_state() != "Disabled":
                say("Disabling the writer's event source mapping ...")
                self.paused_here = True
                self.s.set_mapping(False)
            self.quiesce(tables)

            threading.Thread(target=self.guard, args=(tables,), daemon=True).start()
            todo = [t for t in tables if self.p.phase(t) != "done"]
            say(f"Cleaning {len(todo)} tables, {self.args.workers} at a time ...")
            # Pass 1 runs every table up to its last VACUUM; the pause lets the snapshots that pass 1
            # wrote pass the 60 s retention age, so the last VACUUM keeps only each table's newest one.
            self.run_pass(todo, set(loadable), upto="vacuum3")
            ready = [t for t in todo if self.p.phase(t) in ("vacuum3", "unset", "done")]
            if not self.stop.is_set() and ready:
                say(f"Waiting {RETENTION_WAIT} s for the retention age ...")
                time.sleep(RETENTION_WAIT)
                self.run_pass(ready, set(loadable), upto="done")
        except KeyboardInterrupt:
            self.interrupted()
        except Exception as e:
            self.halt(f"an unexpected error: {e!r}")
        if self.stop.is_set():
            left = [t for t in tables if self.p.phase(t) != "done"]
            print(f"\nSTOPPED with {len(left)} of {len(tables)} tables unfinished"
                  + (f" ({'; '.join(self.stop_reason)})" if self.stop_reason else "") + ".")
            try:
                st = self.s.mapping_state()
            except Exception:
                st = "Disabled"
            if st == "Disabled":
                print("THE WRITER IS STILL PAUSED. Rerun `run` to continue, or `abort` to give up and resume it.")
            else:
                print(f"The writer's event source mapping is {st}, but tables may still have the cleanup's "
                      "short retention. Rerun `run` to continue (it pauses the writer again), or `abort` to "
                      "remove it.")
            sys.exit(1)

        # Not stopped: every table finished or failed on its own, and no statement of ours is running.
        # Undo the failed ones' properties so the writer can resume safely; a later `run` starts them over.
        self.guard_off.set()
        failed = [t for t in tables if self.p.phase(t) != "done"]
        try:
            with cf.ThreadPoolExecutor(self.args.workers) as ex:
                unset_ok = dict(zip(failed, ex.map(self.unset, failed)))
            for t, ok in unset_ok.items():
                if ok:
                    self.p.set_phase(t, "alter")
            say("Re-enabling the writer's event source mapping ...")
            self.s.set_mapping(True)
            visible, _ = self.s.in_flight()
        except Exception as e:
            print(f"\nSTOPPED by an unexpected error: {e!r}")
            print("THE WRITER MAY STILL BE PAUSED. Rerun `run` to continue, or `abort` to give up and resume it.")
            sys.exit(1)
        if failed:
            print(f"\nThe writer is running again, but {len(failed)} of {len(tables)} tables failed:")
            for t in failed:
                note = "" if unset_ok[t] else "; its short retention is still set: run `abort` to remove it"
                print(f"  {t}: {self.failed.get(t, 'failed')}{note}")
            print("Rerun `run` later to retry them, or contact Quilt support with this output.")
            sys.exit(1)
        state_path(self.s.name).rename(state_path(self.s.name).with_suffix(".done.json"))
        print(f"\nDone. The writer is processing the {visible} queued package events; "
              "watch its queue drain in the SQS console.")

    def quiesce(self, tables):
        say("Waiting for the writer's in-flight events and statements to finish ...")
        quiet, deadline = 0, time.time() + 20 * 60
        while quiet < 2:
            _, invisible = self.s.in_flight()
            foreign = self.a.foreign_writes(tables)
            quiet = quiet + 1 if invisible == 0 and not foreign else 0
            if time.time() > deadline:
                if self.paused_here and all(p == "alter" for p in self.p.data["tables"].values()):
                    self.s.set_mapping(True)  # nothing was changed yet: undo this run's pause
                    state_path(self.s.name).unlink()
                    sys.exit("The writer did not go quiet within 20 minutes. Nothing was changed and the "
                             "writer is enabled again; try later.")
                sys.exit("The writer did not go quiet within 20 minutes; its mapping is left DISABLED. "
                         "Rerun `run` to try again, or `abort` to resume it.")
            if quiet < 2:
                time.sleep(60)

    def abort(self):
        tables = sorted(self.p.data.get("tables") or self.s.tables())
        if self.s.mapping_state() == "Disabled":
            # A VACUUM at the cleanup's short retention age must not overlap the writer's writes.
            say("Waiting for statements still writing these tables (an interrupted run's VACUUM) ...")
            deadline = time.time() + 30 * 60
            while self.a.foreign_writes(tables):
                if time.time() > deadline:
                    sys.exit("Statements are still writing these tables after 30 minutes; "
                             "the writer is left DISABLED. Rerun `abort` later.")
                time.sleep(30)
        say(f"Unsetting the cleanup's properties on {len(tables)} tables ...")
        with cf.ThreadPoolExecutor(self.args.workers) as ex:
            failed = [t for t, ok in zip(tables, ex.map(self.unset, tables)) if not ok]
        if failed:
            sys.exit(f"UNSET failed on {len(failed)} tables; the writer is left DISABLED. Rerun `abort`.")
        say("Re-enabling the writer's event source mapping ...")
        self.s.set_mapping(True)
        p = state_path(self.s.name)
        if p.exists():
            p.rename(p.with_suffix(".aborted.json"))
        print("Aborted. The writer is processing its queued events; the tables keep what was done to them.")


def workers(text):
    n = int(text)
    if n < 1:
        raise argparse.ArgumentTypeError("must be 1 or more")
    return n


def main():
    ap = argparse.ArgumentParser(prog="quilt_iceberg_cleanup.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["check", "run", "abort"])
    ap.add_argument("--stack", required=True, help="the Quilt CloudFormation stack's name")
    ap.add_argument("--region", help="the stack's region (default: your AWS configuration's)")
    ap.add_argument("--workers", type=workers, default=4, help="tables cleaned at a time (default 4)")
    ap.add_argument("--since", type=dt.date.fromisoformat,
                    help="check: start the window on this date (YYYY-MM-DD), e.g. the day after a cleanup")
    ap.add_argument("--until", type=dt.date.fromisoformat, help="check: end the window on this date (YYYY-MM-DD)")
    ap.add_argument("--yes", action="store_true", help="run: do not ask for confirmation")
    args = ap.parse_args()
    print(f"quilt_iceberg_cleanup.py {VERSION}", flush=True)
    if args.command == "check":
        check(args)
    elif args.command == "run":
        Cleanup(args).run()
    else:
        Cleanup(args).abort()


if __name__ == "__main__":
    main()
