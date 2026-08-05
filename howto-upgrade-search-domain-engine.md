# Why is my Quilt deployment's search domain still on Elasticsearch 6.8, and how do I upgrade it?

## Tags

`aws`, `elasticsearch`, `opensearch`, `search`, `upgrade`, `cli`, `cloudformation`

*Applies to CloudFormation-based Quilt deployments running releases whose template declares Elasticsearch 7.10 (all current releases). If your release still declares 6.8, upgrade Quilt first — never move the domain ahead of its template. Terraform-based deployments manage the domain through Terraform — contact Quilt support instead of following this article.*

## Summary

Normally you never upgrade the search engine yourself — it rides Quilt's template upgrades. This article covers the exception. Some Quilt deployments run their search domain on Elasticsearch 6.8 even though the deployed CloudFormation template declares 7.10: an engine upgrade fired during a stack update can fail on a transient condition (such as an automated snapshot running at that moment) while CloudFormation records the stack update as successful. Because CloudFormation's normal update flow compares templates against templates, not against the live domain, later deploys never retry; the domain stays behind until someone upgrades it directly.

This article is the direct path: an in-place engine upgrade via the AWS CLI. Only one command in the sequence changes the domain. Two things to know before starting:

- **The upgrade is irreversible** — AWS states it "can't be paused or cancelled," and there is no downgrade. See the rollback options below before running Step 5.
- With Quilt's standard configuration (dedicated master nodes), search keeps serving through the upgrade, though performance may dip while nodes are replaced and Kibana may be unavailable. Masterless cost-sensitive configurations may additionally see a brief unresponsive period after the upgrade. AWS's guidance: the upgrade takes [15 minutes to several hours](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/version-migration.html); large domains can take longer.

The commands use the legacy `aws es` namespace, which matches these domains and takes plain version strings (`7.10`). The newer `aws opensearch` namespace works too, but expects `Elasticsearch_7.10`-style strings.

## Before you start

- **Find your domain and set the variables** every command uses. The search domain belongs to your Quilt CloudFormation stack, logical resource `Search`:

  ```
  aws cloudformation describe-stack-resources --stack-name <your Quilt stack> \
    --query "StackResources[?LogicalResourceId=='Search'].PhysicalResourceId" --output text
  ```

  ```
  DOMAIN=<the domain name from above>
  REGION=<your stack's region>
  TARGET=7.10
  ```

  To confirm the drift, compare the live version with the target:

  ```
  aws es describe-elasticsearch-domain --domain-name $DOMAIN --region $REGION \
    --query 'DomainStatus.ElasticsearchVersion'
  ```

- **Permissions**: `es:DescribeElasticsearchDomain`, `es:GetCompatibleElasticsearchVersions`, `es:GetUpgradeHistory`, `es:GetUpgradeStatus`, and — for the upgrade itself — `es:UpgradeElasticsearchDomain` (grant the newer spellings too if writing a fresh policy: `es:DescribeDomain`, `es:GetCompatibleVersions`, `es:UpgradeDomain`), plus `cloudformation:DescribeStackResources` for the lookup above.

- **Irreversible, but self-protecting**: there's no downgrade, yet the failure paths are covered. If the upgrade *fails*, [AWS restores the cluster automatically](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/version-migration.html) from the snapshot it takes as part of the upgrade — you're back where you started, unharmed. And the data isn't at stake either way: the search index is derived from your S3 buckets and can always be rebuilt in full (a days-long re-index — the backstop of last resort, not a likely event). What doesn't exist is a way back after a *successful* upgrade — which you shouldn't need: 7.10 is the version your Quilt release was built for. AWS's generic advice to [take a manual snapshot first](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/starting-upgrades.html) is optional extra caution here — it preserves a data copy as of that moment (indexing continues past it), restorable only onto a separate domain, and re-pointing a Quilt deployment at a different domain is a guided-migration project, not an undo button.

- **If you run your own clients, dashboards, or saved Kibana objects against the domain** (most deployments don't), review the [Elasticsearch 7 breaking changes](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/version-migration.html) before deciding to upgrade — Quilt's own software and indices are validated on 7.10.

- **Freeze the Quilt stack for the window**: no deploys, no CloudFormation changes, no admin "Re-index and repair" actions while the upgrade runs. If the upgrade were ever to stall — stop making progress for hours; rare, and Step 6 covers the response — the freeze extends until it's resolved, because a domain mid-upgrade refuses further configuration changes.

- **Know your escalation path** (insurance only): technical AWS support cases require a paid support plan — Basic can't open them; as of late 2025 the purchasable tier is Business Support+ (in AWS Organizations, support plans are often managed from the payer account — check with whoever owns that). For a stalled upgrade, self-service triage covers most cases (Step 6), with an AWS case as the final step.

## Step 1 — Read the domain's upgrade history

```
aws es get-upgrade-history --domain-name $DOMAIN --region $REGION
```

This is your baseline: it lists past upgrade attempts and eligibility checks with timestamps, step-by-step results, and — unlike `get-upgrade-status` — the actual failure reasons (`Issues`). On a drifted domain you'll typically see the original failed attempt here. Every later step reads this same command to tell fresh results from stale ones, so note what the latest entry is now.

## Step 2 — Confirm the supported upgrade path

```
aws es get-compatible-elasticsearch-versions --domain-name $DOMAIN --region $REGION
```

From 6.8 the list includes 7.10 (and newer options). **Pick exactly the version your template declares — 7.10 — even though AWS offers newer**: going past the template turns a harmless lag into a mismatch CloudFormation can never reconcile, since downgrades don't exist.

If your domain is below 6.8: within a major version you can jump straight to its last minor (any 6.x → 6.8), but crossing to 7.x requires being on 6.8 first — run this procedure once per hop, and note that ES 6.0–6.7 domains accrue AWS extended-support charges and have an announced end-of-support date, so don't linger there.

## Step 3 — Quick health glance

In the AWS console, the domain should show status **Active** (CLI: `DomainStatus.Processing` is `false`) and cluster health **green** — or your domain's normal color: single-data-node domains sit yellow permanently, and yellow doesn't block upgrades. **Red does** — stop and resolve that first ([AWS guidance](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/handling-errors.html)). Also glance at the console **Notifications** page for any pending maintenance or Auto-Tune action scheduled into your window; if one is there, pick a different window.

## Step 4 — Run the eligibility check

This validates without upgrading — AWS's words: it "does not actually perform the upgrade":

```
aws es upgrade-elasticsearch-domain --domain-name $DOMAIN --region $REGION \
  --target-version $TARGET --perform-check-only
```

The check runs asynchronously, usually a few minutes. Fetch the verdict with Step 1's command — the new entry appears with a fresh timestamp and a name like "Pre-Upgrade Check for Elasticsearch 7.10":

```
aws es get-upgrade-history --domain-name $DOMAIN --region $REGION
```

- **`SUCCEEDED`** → proceed to Step 5 promptly: a passing check also means no automated snapshot is running right now (AWS takes them hourly, and they block upgrades), so you're in the gap. No need to rush beyond ordinary promptness — if the gap closes, the worst case is a harmless failed attempt and a retry.
- **Failed with a snapshot-related `Issue`** (e.g. "prior snapshot operation has not yet completed") → normal and harmless. Wait 10–15 minutes, re-run the check.
- **Failed with anything else** → the `Issues` text names the condition; most match AWS's [validation-failure table](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/version-migration.html) with self-service fixes. Involve Quilt support if the fix touches Quilt-managed resources.
- **`SUCCEEDED_WITH_ISSUES`** → don't proceed; send the full history output to Quilt support first.

## Step 5 — Run the upgrade

The one command that changes the domain:

```
aws es upgrade-elasticsearch-domain --domain-name $DOMAIN --region $REGION \
  --target-version $TARGET
```

It returns immediately with a JSON echo of the request. If it errors instead (for example, the domain slipped into a processing state), nothing has happened — resolve and return to Step 4.

## Step 6 — Watch it

Re-run the Step 1 history command occasionally (it shows the current attempt's steps and `ProgressPercent`), or watch the domain page in the console. The upgrade proceeds `PRE_UPGRADE_CHECK` → `SNAPSHOT` → `UPGRADE`. If the upgrade's own early steps fail (the snapshot gap can close), the domain is unharmed and still on 6.8 — return to Step 4.

**Done** means: `aws es describe-elasticsearch-domain` shows `ElasticsearchVersion: "7.10"` and `Processing: false`.

If `ProgressPercent` sits unchanged for several hours: the domain typically keeps serving search meanwhile, and AWS's [stuck-upgrade guidance](https://repost.aws/knowledge-center/opensearch-stuck-failed-upgrade) prescribes self-service triage first — check `FreeStorageSpace`, cluster status, and JVM pressure in CloudWatch, free disk if it's low — and an AWS technical support case if none of that resolves it. Quilt support can help assemble the details AWS will ask for.

One cost note: the upgrade is a blue/green deployment; [AWS charges for the largest cluster during the first hour only](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/managedomains-configuration-changes.html), then for a single cluster even while the deployment continues — a one-time blip, not a rate change.

## Step 7 — Confirm and clean up

1. Re-run the version check (see **Done** above) — this is the fact you came for.
2. Upload a small test file to a registered bucket you're comfortable writing to, and confirm it appears in catalog search. Right after an upgrade the indexing backlog may need time — give it up to ~15 minutes before reading anything into a delay. Delete the test file when done. (Read-only alternative: run a search whose results you know.)
3. Nothing else is needed: S3 event notifications queue and retry, so objects uploaded during the window get indexed without any re-index step, and there is nothing to re-enable.
4. Tell Quilt support the upgrade completed — a copy of the version-check output is perfect — so we can plan any follow-up work with you.

## Related

- [Upgrading Amazon OpenSearch Service domains](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/version-migration.html) — AWS's reference for the upgrade process
- [How do I collect search-cluster diagnostics for Quilt support?](https://github.com/quiltdata/knowledge-base/blob/main/howto-collect-search-cluster-diagnostics.md)
