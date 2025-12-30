# EventBridge Routing Issue - RESOLVED ✅

**Status:** RESOLVED | **Date:** 2025-12-29 | **Root Cause:** Missing SNS→SQS subscriptions and policies

## TL;DR

Customer's S3 events weren't reaching Quilt's processing pipeline. While the EventBridge rule was initially disabled (and enabling it appeared to fix the issue), deeper testing revealed the **actual problem**: critical SQS queues weren't subscribed to the SNS topic and lacked proper policies.

**The Complete Fix:**

```bash
# Step 1: Enable EventBridge rule (initial fix)
aws events enable-rule --name cloudtrail-to-sns --region us-east-1

# Step 2: Subscribe ManifestIndexerQueue to SNS (the real fix for packages)
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:712023778557:quilt-eventbridge-test-QuiltNotifications-9b3c8cea-3f73-4e6c-8b82-ab5260687e45 \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:us-east-1:712023778557:quilt-staging-ManifestIndexerQueue-uh1K3XwaAR2k \
  --region us-east-1

# Step 3: Add SQS policy to ManifestIndexerQueue
aws sqs set-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/712023778557/quilt-staging-ManifestIndexerQueue-uh1K3XwaAR2k \
  --attributes '{"Policy":"{\"Version\":\"2012-10-17\",\"Id\":\"SQSPolicy\",\"Statement\":[{\"Sid\":\"SQSEventPolicy\",\"Effect\":\"Allow\",\"Principal\":\"*\",\"Action\":\"SQS:SendMessage\",\"Resource\":\"arn:aws:sqs:us-east-1:712023778557:quilt-staging-ManifestIndexerQueue-uh1K3XwaAR2k\",\"Condition\":{\"ArnEquals\":{\"aws:SourceArn\":\"arn:aws:sns:us-east-1:712023778557:quilt-eventbridge-test-QuiltNotifications-9b3c8cea-3f73-4e6c-8b82-ab5260687e45\"}}}]}"}' \
  --region us-east-1

# Step 4: Subscribe EsIngestQueue to SNS (the real fix for object indexing)
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:712023778557:quilt-eventbridge-test-QuiltNotifications-9b3c8cea-3f73-4e6c-8b82-ab5260687e45 \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:us-east-1:712023778557:quilt-staging-EsIngestQueue-ouyPwAl203Ui \
  --region us-east-1

# Step 5: Add SQS policy to EsIngestQueue
aws sqs set-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/712023778557/quilt-staging-EsIngestQueue-ouyPwAl203Ui \
  --attributes '{"Policy":"{\"Version\":\"2012-10-17\",\"Id\":\"SQSPolicy\",\"Statement\":[{\"Sid\":\"SQSEventPolicy\",\"Effect\":\"Allow\",\"Principal\":\"*\",\"Action\":\"SQS:SendMessage\",\"Resource\":\"arn:aws:sqs:us-east-1:712023778557:quilt-staging-EsIngestQueue-ouyPwAl203Ui\",\"Condition\":{\"ArnEquals\":{\"aws:SourceArn\":\"arn:aws:sns:us-east-1:712023778557:quilt-eventbridge-test-QuiltNotifications-9b3c8cea-3f73-4e6c-8b82-ab5260687e45\"}}}]}"}' \
  --region us-east-1
```

## Key Takeaways

### 1. Test the Complete Pipeline, Not Just Individual Components

The EventBridge rule appeared to work after enabling it (metrics showed triggers and SNS messages). However, **the Lambda functions weren't being invoked** because messages weren't reaching the correct queues. Always verify end-to-end processing, not just intermediate steps.

### 2. SNS Fan-Out Requires All Consumer Subscriptions

SNS was publishing to 3 queues, but the 2 most critical queues for processing were missing:

- `ManifestIndexerQueue` (package indexing)
- `EsIngestQueue` (object/ES indexing)

Just because some subscriptions exist doesn't mean all necessary ones are configured.

### 3. SQS Policies Must Allow SNS as Source

Even with subscriptions in place, messages will be silently dropped if the SQS queue policy doesn't explicitly allow the SNS topic to send messages. Both queues had **no policy** initially.

### 4. Lambda Event Source Mappings Can Be Misleading

Lambda was configured to listen to queues with different names than those receiving SNS messages:

- Lambda watched: `ManifestIndexerQueue`
- SNS sent to: `IndexerQueue` (different queue!)

This mismatch went undetected because both queues existed and had similar names.

## The Problem

Events from S3 → CloudTrail → EventBridge → SNS → SQS weren't reaching the Quilt indexer. Customer followed EventBridge routing documentation but events weren't being processed.

## The Investigation

### Phase 1: Initial Discovery (Correct but Incomplete)

Initial hypotheses (all incorrect):

- ❌ CloudTrail wasn't sending events to EventBridge
- ❌ SNS wasn't connected to quilt-staging queues
- ❌ Bucket wasn't in CloudTrail event selectors

First issue found:

- ✅ EventBridge rule `cloudtrail-to-sns` was in `DISABLED` state

After enabling the rule, metrics showed the pipeline was working (176 EventBridge triggers, 178 SNS messages published). **This was prematurely declared as resolved.**

### Phase 2: End-to-End Testing Revealed the Real Issues

When testing actual package creation and object indexing, **nothing worked**. Deeper investigation revealed:

#### Root Cause 1: Missing SNS Subscriptions

- SNS had 3 subscriptions, but critical queues were missing:
  - ❌ `ManifestIndexerQueue` not subscribed (package indexing broken)
  - ❌ `EsIngestQueue` not subscribed (object indexing broken)
- Messages flowed to wrong queues that no Lambda was watching
- EventBridge → SNS was working, but Lambda functions never got invoked

#### Root Cause 2: Missing SQS Policies

- Both `ManifestIndexerQueue` and `EsIngestQueue` had **no policy**
- Even after subscribing them to SNS, messages would be rejected
- Policy needed to explicitly allow SNS topic as source

#### Root Cause 3: Queue Name Confusion

- Lambda `ManifestIndexerLambda` watched: `quilt-staging-ManifestIndexerQueue-uh1K3XwaAR2k`
- SNS published to: `quilt-staging-IndexerQueue-yD8FCAN9MJWr` (different queue!)
- Both queues exist, creating a false sense that the wiring was correct

## Verified Working Flow

```text
S3 Upload (quilt-eventbridge-test)
    ↓
CloudTrail (analytics trail)
    ↓
EventBridge (aws.s3 events)
    ↓
Rule: cloudtrail-to-sns [ENABLED] ✅
    ↓
SNS: quilt-eventbridge-test-QuiltNotifications ✅
    ├─→ SQS: PkgEventsQueue
    ├─→ SQS: IndexerQueue
    ├─→ SQS: S3SNSToEventBridgeQueue
    ├─→ SQS: ManifestIndexerQueue ✅ (FIXED - added subscription + policy)
    │       ↓
    │   Lambda: ManifestIndexerLambda
    │   (Package indexing - creates packages in catalog)
    │
    └─→ SQS: EsIngestQueue ✅ (FIXED - added subscription + policy)
            ↓
        Lambda: EsIngestLambda
        (Object indexing - updates Elasticsearch for search)
```

## Test Results

### Initial Test (Incomplete)

| Metric | Result |
| ------ | ------ |
| EventBridge rule triggered | ✅ 176 events |
| SNS messages published | ✅ 178 messages |
| SQS messages delivered | ✅ 178 messages |
| **Pipeline end-to-end** | ❌ **NOT working** |

### After Complete Fix

| Metric | Result |
| ------ | ------ |
| EventBridge rule triggered | ✅ Working |
| SNS messages published | ✅ Working |
| ManifestIndexerQueue messages | ✅ 2 messages received |
| EsIngestQueue messages | ✅ 1 message received |
| Package indexing (ManifestIndexer) | ✅ Working |
| Object indexing (EsIngest) | ✅ Working |
| **Pipeline end-to-end** | ✅ **Fully working** |

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

## Verification Commands

### Complete End-to-End Verification

To verify the entire pipeline is working:

```bash
# 1. Upload test file
echo "Test $(date)" > test.txt
aws s3 cp test.txt s3://quilt-eventbridge-test/test/test.txt --region us-east-1

# 2. Wait 2-3 minutes for CloudTrail processing
sleep 180

# 3. Check EventBridge rule triggered
echo "=== EventBridge Triggers ==="
aws cloudwatch get-metric-statistics \
  --namespace AWS/Events \
  --metric-name TriggeredRules \
  --dimensions Name=RuleName,Value=cloudtrail-to-sns \
  --start-time $(date -u -v-5M '+%Y-%m-%dT%H:%M:%S') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%S') \
  --period 60 \
  --statistics Sum \
  --region us-east-1

# 4. Check SNS published messages
echo "=== SNS Messages Published ==="
aws cloudwatch get-metric-statistics \
  --namespace AWS/SNS \
  --metric-name NumberOfMessagesPublished \
  --dimensions Name=TopicName,Value=quilt-eventbridge-test-QuiltNotifications-9b3c8cea-3f73-4e6c-8b82-ab5260687e45 \
  --start-time $(date -u -v-5M '+%Y-%m-%dT%H:%M:%S') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%S') \
  --period 60 \
  --statistics Sum \
  --region us-east-1

# 5. Check ManifestIndexerQueue received messages
echo "=== ManifestIndexerQueue Messages ==="
aws cloudwatch get-metric-statistics \
  --namespace AWS/SQS \
  --metric-name NumberOfMessagesReceived \
  --dimensions Name=QueueName,Value=quilt-staging-ManifestIndexerQueue-uh1K3XwaAR2k \
  --start-time $(date -u -v-5M '+%Y-%m-%dT%H:%M:%S') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%S') \
  --period 60 \
  --statistics Sum \
  --region us-east-1

# 6. Check EsIngestQueue received messages
echo "=== EsIngestQueue Messages ==="
aws cloudwatch get-metric-statistics \
  --namespace AWS/SQS \
  --metric-name NumberOfMessagesReceived \
  --dimensions Name=QueueName,Value=quilt-staging-EsIngestQueue-ouyPwAl203Ui \
  --start-time $(date -u -v-5M '+%Y-%m-%dT%H:%M:%S') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%S') \
  --period 60 \
  --statistics Sum \
  --region us-east-1

# 7. Check Lambda invocations
echo "=== Lambda Invocations ==="
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=quilt-staging-ManifestIndexerLambda-kYYtGJDEOYmU \
  --start-time $(date -u -v-5M '+%Y-%m-%dT%H:%M:%S') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%S') \
  --period 60 \
  --statistics Sum \
  --region us-east-1
```

### Expected Results

All metrics should show non-zero counts after waiting for CloudTrail processing:

- EventBridge: Should show triggered rules
- SNS: Should show published messages
- ManifestIndexerQueue: Should show received messages
- EsIngestQueue: Should show received messages
- Lambda: Should show invocations

## Related Documentation

- Quilt EventBridge Documentation: <https://docs.quilt.bio/quilt-platform-administrator/advanced/eventbridge>
- Customer originally following SNS Fanout + EventBridge Routing patterns

---

## Final Summary

**Investigation:** Two-phase debugging - initial fix appeared successful but end-to-end testing revealed deeper issues

**Resolution time:**

- Phase 1: ~2 hours investigation, 1 second fix (EventBridge rule enable)
- Phase 2: ~30 minutes investigation, 5 commands to fix (SNS subscriptions + SQS policies)

**Lessons Learned:**

1. **Always test end-to-end**: Intermediate metrics (EventBridge triggers, SNS publishes) can show "success" while the actual processing fails
2. **Verify Lambda invocations**: The ultimate test is whether Lambda functions process events, not just whether queues receive messages
3. **Check all SNS subscriptions**: Fan-out architectures need ALL required subscriptions configured
4. **SQS policies are critical**: Even with subscriptions, messages are silently dropped without proper IAM policies
5. **Queue naming matters**: Similar queue names (`IndexerQueue` vs `ManifestIndexerQueue`) can create confusion about the actual data flow
