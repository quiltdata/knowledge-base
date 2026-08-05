# How do I upgrade my Quilt deployment's search domain engine (Elasticsearch 6.8 → 7.10)?

## Tags

`aws`, `elasticsearch`, `opensearch`, `search`, `upgrade`, `cli`, `cloudformation`

## Summary

Some Quilt deployments run their search domain on Elasticsearch 6.8 even though the deployed CloudFormation template declares 7.10: an engine upgrade fired during a stack update can fail on a transient condition — most commonly an automated snapshot running at that moment — while CloudFormation records the stack update as successful. Because CloudFormation compares templates against templates, not against the live domain, later deploys never retry; the domain stays behind until someone upgrades it directly.

This article is the direct path: an in-place engine upgrade via the AWS CLI, in a short sequence where **every command is read-only except one** — the upgrade trigger itself. Search keeps serving throughout (performance may dip while nodes are replaced; Kibana may be unavailable). Expect minutes to hours depending on data size; plan for the possibility of most of a day on large domains.

To check whether this applies to you: compare the live engine version with what your template declares.

```
aws es describe-elasticsearch-domain --domain-name $DOMAIN --region $REGION \
  --query 'DomainStatus.ElasticsearchVersion'
```

(`aws es list-domain-names` shows your domain name. Quilt support can tell you what your release declares — for current releases it is 7.10.)

## Before you start

- **Set the variables** used by every command below:

  ```
  DOMAIN=<your search domain name>
  REGION=<your stack's region>
  ```

- **Permissions**: the credentials you use need `es:DescribeElasticsearchDomain`, `es:GetCompatibleElasticsearchVersions`, `es:GetUpgradeStatus`, `es:DescribeDomainAutoTunes`, and — for the one state-changing step — `es:UpgradeElasticsearchDomain`.

- **Freeze the Quilt stack for the window**: no deploys, no CloudFormation changes, no admin "Re-index and repair" actions while the upgrade runs. The domain must be the only thing changing.

- **Know your escalation path** (insurance only): which AWS support plan is on the account (the Support Center page shows it), and who could open a technical case. In the rare case an upgrade stalls, the domain keeps serving search — it just refuses further changes until AWS support unsticks it, and Business-or-above support is the channel for that. Basic is workable too: Business support enables in minutes with immediate effect, so the real preparation is knowing who can approve it.

## Step 1 — Confirm the target version is a legal hop

```
aws es get-compatible-elasticsearch-versions --domain-name $DOMAIN --region $REGION
```

From 6.8, the list includes 7.10 — proceed with `TARGET=7.10`.

If your domain is on a version **below** 6.8, note that 7.10 will not be in the list: Elasticsearch upgrades one step at a time (for example 6.7 → 6.8, then 6.8 → 7.10). Run this whole procedure once per hop.

## Step 2 — Check nothing is scheduled to interfere

```
aws es describe-domain-auto-tunes --domain-name $DOMAIN --region $REGION
```

If no Auto-Tune action is scheduled for the coming day, proceed. If one is scheduled inside your window, move the window (or contact Quilt support about disabling Auto-Tune — the disable itself has options that matter).

Also glance at the domain in the AWS console: cluster health should be green and the domain status Active before you continue.

## Step 3 — Run the eligibility check

This validates the upgrade without performing it — despite the command name, `--perform-check-only` changes nothing on the domain:

```
aws es upgrade-elasticsearch-domain --domain-name $DOMAIN --region $REGION \
  --target-version $TARGET --perform-check-only
```

The check runs asynchronously. Fetch the verdict (repeat until the check completes — usually a few minutes):

```
aws es get-upgrade-status --domain-name $DOMAIN --region $REGION
```

- **`PRE_UPGRADE_CHECK: SUCCEEDED`** → go directly to Step 4, *now*. A passing check also means no automated snapshot is running at this moment — that is exactly the gap you want to launch into, because AWS takes hourly automated snapshots and an upgrade colliding with one fails.
- **Failed with "Prior snapshot operation has not yet completed"** → normal and harmless; an automated snapshot is running. Wait 10–15 minutes and repeat this step. (See [AWS's article on this error](https://repost.aws/knowledge-center/opensearch-prior-snapshot-error).)
- **Failed with anything else** → stop and send the output to Quilt support before proceeding.

## Step 4 — Run the upgrade

The one state-changing command:

```
aws es upgrade-elasticsearch-domain --domain-name $DOMAIN --region $REGION \
  --target-version $TARGET
```

## Step 5 — Watch it

Re-run the Step 3 status command occasionally, or watch the domain page in the console. The upgrade proceeds through `PRE_UPGRADE_CHECK` → `SNAPSHOT` → `UPGRADE` and takes anywhere from minutes to hours ([AWS's guidance on long-running upgrades](https://repost.aws/knowledge-center/opensearch-domain-upgrade)).

If progress sits unchanged for several hours: **don't touch anything**. The domain keeps serving search while stuck; the recovery path is an AWS support case ([AWS's article on stuck upgrades](https://repost.aws/knowledge-center/opensearch-stuck-failed-upgrade)) — and contact Quilt support, we've been through this and will help draft the case.

## Step 6 — Smoke test

After the status shows the upgrade succeeded:

1. Upload a small file to any bucket registered in your Quilt catalog.
2. Confirm it appears in catalog search within a couple of minutes.
3. Run a search you know should return results.

If anything looks off, contact Quilt support — and tell us the upgrade completed either way, so we can verify from our side and plan any follow-up work with you.

## Related

- [Upgrading Amazon OpenSearch Service domains](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/version-migration.html) — AWS's reference for the upgrade process
- [How do I collect search-cluster diagnostics for Quilt support?](howto-collect-search-cluster-diagnostics.md)
