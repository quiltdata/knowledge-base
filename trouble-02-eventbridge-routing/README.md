# EventBridge Routing Issue - RESOLVED ✅

**Status:** RESOLVED | **Date:** 2025-12-29 | **Root Cause:** Disabled EventBridge rule

## TL;DR

Customer's S3 events weren't reaching Quilt's processing pipeline via EventBridge. The infrastructure was correctly configured—someone had simply disabled the EventBridge rule. Re-enabling it immediately fixed the issue.

**The Fix:**

```bash
aws events enable-rule --name cloudtrail-to-sns --region us-east-1
```

## Key Takeaways

### 1. Always Check Rule States First

Before investigating CloudTrail, SNS, or SQS issues, verify EventBridge rules are enabled:

```bash
aws events describe-rule --name <rule-name> --region us-east-1 --query 'State'
```

### 2. CloudTrail→EventBridge Integration is Automatic

When CloudTrail has data event selectors configured, events automatically flow to EventBridge. There's no separate "enable EventBridge" toggle needed (as of 2024).

### 3. Purpose-Built Infrastructure Exists

The `quilt-eventbridge-test` bucket was already set up with:

- ✅ CloudTrail event selectors
- ✅ EventBridge rule (`cloudtrail-to-sns`)
- ✅ SNS topic connected to quilt-staging queues
- ✅ Complete end-to-end pipeline

It just needed the rule enabled.

## The Problem

Events from S3 → CloudTrail → EventBridge → SNS → SQS weren't reaching the Quilt indexer. Customer followed EventBridge routing documentation but events weren't being processed.

## The Investigation

Initial hypotheses (all incorrect):

- ❌ CloudTrail wasn't sending events to EventBridge
- ❌ SNS wasn't connected to quilt-staging queues
- ❌ Bucket wasn't in CloudTrail event selectors

Actual issue:

- ✅ EventBridge rule `cloudtrail-to-sns` was in `DISABLED` state

## Verified Working Flow

```text
S3 Upload (quilt-eventbridge-test)
    ↓
CloudTrail (analytics trail)
    ↓
EventBridge (aws.s3 events)
    ↓
Rule: cloudtrail-to-sns [ENABLED]
    ↓
SNS: quilt-eventbridge-test-QuiltNotifications
    ↓
SQS: quilt-staging queues (3)
    ↓
Lambda: Processing ✅
```

## Test Results

| Metric | Result |
| ------ | ------ |
| EventBridge rule triggered | ✅ 1 event |
| SNS messages published | ✅ 1 message |
| SQS messages delivered | ✅ Success |
| Pipeline end-to-end | ✅ Working |

## Documentation

### Primary

- **[SUCCESS-REPORT.md](SUCCESS-REPORT.md)** - Complete resolution with test data and metrics
- **[config-quilt-eventbridge-test.toml](config-quilt-eventbridge-test.toml)** - Working configuration reference

### Supporting

- **[test-plan-staging.md](test-plan-staging.md)** - Investigation methodology
- **[customer-issue-summary.md](customer-issue-summary.md)** - Original problem statement
- **[ACTION-ITEMS.md](ACTION-ITEMS.md)** - Follow-up tasks

### Archives

- **backup-policies/** - SNS policy backups and modifications
- **test-artifacts/** - Test execution files and logs
- **obsolete-reports/** - Superseded investigation documents

## Verification Command

To verify the system is working:

```bash
# Upload test file
echo "Test $(date)" > test.txt
aws s3 cp test.txt s3://quilt-eventbridge-test/test/test.txt --region us-east-1

# Wait 2 minutes for CloudTrail
sleep 120

# Check EventBridge triggers
aws cloudwatch get-metric-statistics \
  --namespace AWS/Events \
  --metric-name TriggeredRules \
  --dimensions Name=RuleName,Value=cloudtrail-to-sns \
  --start-time $(date -u -v-5M '+%Y-%m-%dT%H:%M:%S') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%S') \
  --period 60 \
  --statistics Sum \
  --region us-east-1
```

## Related Documentation

- Quilt EventBridge Documentation: <https://docs.quilt.bio/quilt-platform-administrator/advanced/eventbridge>
- Customer originally following SNS Fanout + EventBridge Routing patterns

---

**Investigation:** Automated orchestration with cloud architect agents
**Resolution time:** ~2 hours investigation, 1 second fix
**Lesson:** Check simple things (rule state) before complex things (CloudTrail config)
