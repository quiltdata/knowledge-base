# EventBridge Routing Investigation - Failure Report

**Status:** PARTIALLY RESOLVED | **Date:** 2025-12-29
**Infrastructure:** Fixed | **Application:** Broken (Lambda code issue)

## Executive Summary

While the initial EventBridge routing issue was resolved (enabling the disabled rule), comprehensive end-to-end testing revealed **the package indexing pipeline is fundamentally broken**. The infrastructure now routes events correctly, but the ManifestIndexer Lambda fails 100% of the time due to message format incompatibility.

**Bottom Line:** Packages created in `s3://quilt-eventbridge-test` do **not** appear in the package catalog. Object indexing (Elasticsearch) works, but package manifest indexing fails.

## Timeline of Investigation

### Phase 1: Initial Fix (Incomplete) ✅
- **Issue:** EventBridge rule `cloudtrail-to-sns` was DISABLED
- **Fix:** `aws events enable-rule --name cloudtrail-to-sns`
- **Result:** Metrics showed 176+ events flowing through the pipeline
- **False Conclusion:** Declared as "resolved" based on metrics alone

### Phase 2: Missing Subscriptions (Fixed) ✅
- **Issue:** Critical SQS queues weren't subscribed to SNS
- **Missing:** `ManifestIndexerQueue` and `EsIngestQueue`
- **Fix:** Added SNS subscriptions + SQS policies
- **Result:** Messages now reach both queues

### Phase 3: Lambda Code Incompatibility (UNRESOLVED) ❌
- **Issue:** ManifestIndexer Lambda expects EventBridge format, receives SNS format
- **Error:** `KeyError: 'detail'` in `t4_lambda_manifest_indexer/__init__.py:263`
- **Impact:** 100% failure rate (60+ errors out of 58 invocations)
- **Result:** **Package indexing completely non-functional**

## Root Cause Analysis

### Architectural Mismatch

The system has a **fundamental design incompatibility**:

```
ARCHITECTURE:
EventBridge → SNS Topic → SQS Queue → Lambda

LAMBDA EXPECTATION:
event['detail']  # Native EventBridge format

ACTUAL MESSAGE FORMAT:
{
  "Records": [{
    "body": "{...SNS message...}",
    "messageAttributes": {...},
    "...": "..."
  }]
}

Where body contains:
{
  "Message": "{...EventBridge event as JSON string...}",
  "TopicArn": "...",
  "...": "..."
}
```

### Why This Happened

1. **Lambda was designed for direct EventBridge events**, not SNS-wrapped events
2. **Infrastructure uses SNS fan-out pattern** for multiple consumers
3. **No one tested end-to-end** after the EventBridge rule was disabled
4. **The disconnect went unnoticed** because metrics showed "success" at each layer

## Evidence

### Lambda Logs (100% Failure)

```
2025-12-30T05:38:16 [ERROR] KeyError: 'detail'
Traceback (most recent call last):
  File "./t4_lambda_manifest_indexer/__init__.py", line 263, in handler
```

**Every invocation fails with the same error.**

### CloudWatch Metrics

| Metric | Value | Interpretation |
|--------|-------|----------------|
| EventBridge rule triggered | 176 events | ✅ Working |
| SNS messages published | 178 messages | ✅ Working |
| ManifestIndexerQueue received | 60+ messages | ✅ Working |
| Lambda invocations | 58 invocations | ✅ Triggered |
| Lambda errors | 60+ errors | ❌ **100% failure** |
| Packages indexed | **0** | ❌ **Nothing works** |

### Test Results

**Created package:** `ernie/pipeline-test@84e04ad466`
- ✅ Manifest file created: `.quilt/packages/84e04ad466...`
- ✅ Named package pointer: `.quilt/named_packages/ernie/pipeline-test/latest`
- ✅ EventBridge triggered
- ✅ SNS published
- ✅ Queue received message
- ✅ Lambda invoked
- ❌ **Lambda failed with KeyError**
- ❌ **Package NOT in catalog**

## Hypotheses & Validation

### Hypothesis 1: Missing SNS Subscription ❌ (Incorrect)
**Theory:** ManifestIndexerQueue wasn't subscribed to SNS
**Test:** Added subscription
**Result:** Messages reached queue, but Lambda still failed

### Hypothesis 2: Wrong Message Format ✅ (CORRECT)
**Theory:** Lambda expects EventBridge format, receives SNS format
**Test:** Examined Lambda logs
**Result:** Confirmed - `KeyError: 'detail'` because event structure is wrong

### Hypothesis 3: Dual-Target Confusion ✅ (Contributing Factor)
**Theory:** Sending to both SNS and directly to SQS causes issues
**Test:** Consulted cloud architect agent
**Result:** Dual-targeting is anti-pattern, causes message duplication

### Hypothesis 4: Queue Policy Issue ❌ (Ruled Out)
**Theory:** Missing EventBridge → SQS permissions
**Test:** Added EventBridge as direct target
**Result:** Didn't fix the underlying Lambda code issue

## Architecture Analysis

### Current (Broken) Flow

```
S3 Upload
    ↓
CloudTrail (analytics trail)
    ↓
EventBridge Rule: cloudtrail-to-sns
    ↓
SNS: quilt-eventbridge-test-QuiltNotifications
    ├─→ SQS: PkgEventsQueue
    ├─→ SQS: IndexerQueue → Lambda: SearchHandler (works)
    ├─→ SQS: S3SNSToEventBridgeQueue
    ├─→ SQS: ManifestIndexerQueue → Lambda: ManifestIndexer (BROKEN)
    │                                        ↓
    │                                   KeyError: 'detail'
    │                                   100% failure rate
    │
    └─→ SQS: EsIngestQueue → Lambda: EsIngest (works)
```

### What Needs to Happen

**Option A: Fix Lambda Code** (Recommended)
```python
def lambda_handler(event, context):
    for record in event['Records']:
        # Extract SNS message
        sns_message = json.loads(record['body'])

        # Extract EventBridge event from SNS wrapper
        eventbridge_event = json.loads(sns_message['Message'])

        # Now access detail
        detail = eventbridge_event['detail']

        # Process...
```

**Option B: Change Architecture** (Not Recommended)
- Remove SNS fan-out
- Use direct EventBridge → SQS routing
- Requires reconfiguring entire pipeline

### Comparison: Working vs. Broken Lambda

**SearchHandler (Works):**
- Listens to: `IndexerQueue`
- Handles: SNS-wrapped messages correctly
- Result: ✅ Object indexing works

**ManifestIndexer (Broken):**
- Listens to: `ManifestIndexerQueue`
- Expects: Native EventBridge format
- Receives: SNS-wrapped messages
- Result: ❌ Crashes with KeyError

## Impact Assessment

### What Works ✅

1. EventBridge rule triggers correctly
2. SNS fan-out delivers to all queues
3. EsIngestQueue → EsIngest Lambda (object indexing)
4. IndexerQueue → SearchHandler Lambda (search indexing)
5. Infrastructure permissions are correct

### What's Broken ❌

1. **Package manifest indexing** - 100% failure rate
2. **Package catalog listings** - packages don't appear
3. **ManifestIndexer Lambda** - incompatible with SNS format

### User Impact

**Symptom:** "I created a package but it doesn't show up in the package listing"

**Reason:** ManifestIndexer Lambda fails silently:
- No visible error to user
- CloudWatch shows errors but no DLQ escalation
- Package exists in S3 but not indexed in catalog
- Search works (different Lambda), but package browsing broken

## Recommended Fixes

### Immediate Fix (Required)

**Update ManifestIndexer Lambda Code:**

```python
# File: t4_lambda_manifest_indexer/__init__.py
# Line ~263

def handler(event, context):
    """
    Handler for SQS events containing SNS-wrapped EventBridge messages
    """
    for record in event['Records']:
        # SQS delivers SNS messages in the body
        message_body = json.loads(record['body'])

        # SNS wraps EventBridge events in the Message field
        eventbridge_event = json.loads(message_body['Message'])

        # Now we can access the detail field
        detail = eventbridge_event.get('detail', {})

        # Extract S3 event info
        bucket = detail.get('requestParameters', {}).get('bucketName')
        key = detail.get('requestParameters', {}).get('key')

        # Process manifest...
        process_manifest(bucket, key)
```

### Infrastructure Changes (Cleanup)

1. **Remove incorrect SNS subscription** (if re-added):
   ```bash
   # Don't subscribe ManifestIndexerQueue to SNS until Lambda is fixed
   ```

2. **Add monitoring** for Lambda errors:
   ```bash
   aws cloudwatch put-metric-alarm \
     --alarm-name ManifestIndexer-High-Error-Rate \
     --metric-name Errors \
     --namespace AWS/Lambda \
     --statistic Sum \
     --period 300 \
     --threshold 10 \
     --comparison-operator GreaterThanThreshold \
     --dimensions Name=FunctionName,Value=quilt-staging-ManifestIndexerLambda-kYYtGJDEOYmU
   ```

3. **Configure DLQ escalation** to catch failures

### Testing Procedure (Post-Fix)

```bash
# 1. Deploy updated Lambda code

# 2. Re-add SNS subscription
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:712023778557:quilt-eventbridge-test-QuiltNotifications-9b3c8cea-3f73-4e6c-8b82-ab5260687e45 \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:us-east-1:712023778557:quilt-staging-ManifestIndexerQueue-uh1K3XwaAR2k \
  --region us-east-1

# 3. Create test package
quilt3 push ernie/test-package s3://quilt-eventbridge-test/

# 4. Wait 3 minutes for CloudTrail

# 5. Verify package appears in catalog
# Check: https://nightly.quilttest.com/b/quilt-eventbridge-test/packages

# 6. Check Lambda logs for success (not errors)
aws logs tail /quilt/quilt-staging/ManifestIndexerLambda --since 5m --region us-east-1
```

## Lessons Learned

### 1. Metrics Are Not End-to-End Tests

**What Happened:** Declared success based on:
- EventBridge triggers: ✅
- SNS publishes: ✅
- SQS receives: ✅

**What We Missed:** Lambda was failing 100% of the time

**Lesson:** Always verify **final output** (package appears in catalog), not just intermediate metrics.

### 2. Message Format Compatibility Matters

**What Happened:** Lambda designed for Format A, infrastructure delivers Format B

**Why It Happened:**
- Lambda code written expecting direct EventBridge events
- Infrastructure evolved to use SNS fan-out
- No one tested the integration

**Lesson:** When event sources change, verify Lambda handlers are compatible.

### 3. Silent Failures Are Dangerous

**What Happened:** Lambda failed for weeks/months without alerting

**Why It Happened:**
- No CloudWatch alarms on Lambda errors
- No DLQ escalation policy
- Errors logged but not monitored

**Lesson:** Set up proactive monitoring for critical paths.

### 4. Architecture Mismatches Create Technical Debt

**What Happened:** Two different patterns coexist:
- SearchHandler correctly handles SNS format
- ManifestIndexer expects EventBridge format

**Why It Happened:** Incremental changes without architectural review

**Lesson:** Standardize message handling patterns across all Lambdas.

### 5. Test With Real Use Cases

**What Happened:** All our tests used S3 file uploads, not package creation

**Why It Matters:** File uploads trigger events but don't test manifest indexing

**Lesson:** Test actual user workflows (create package, verify in catalog).

## Current State

### Infrastructure Status ✅

All infrastructure components are correctly configured:
- ✅ EventBridge rule enabled
- ✅ SNS topic receiving events
- ✅ EsIngestQueue subscribed + working
- ✅ Queue policies correct
- ✅ Event flow working end-to-end

### Application Status ❌

**BLOCKED:** Lambda code incompatibility

- ❌ ManifestIndexer Lambda requires code fix
- ❌ Cannot subscribe ManifestIndexerQueue until Lambda is fixed
- ❌ Package indexing non-functional
- ❌ Users cannot see packages in catalog

### Next Steps

1. **Immediate:** File bug report for ManifestIndexer Lambda code fix
2. **Short-term:** Deploy Lambda code update with SNS unwrapping
3. **Medium-term:** Add comprehensive monitoring and alerting
4. **Long-term:** Audit all Lambdas for message format consistency

## Conclusion

The EventBridge routing issue has **three layers of problems**:

1. **Layer 1 (FIXED):** Disabled EventBridge rule ✅
2. **Layer 2 (FIXED):** Missing SNS subscriptions and policies ✅
3. **Layer 3 (UNRESOLVED):** Lambda code incompatibility ❌

**The package indexing pipeline remains broken until the Lambda code is updated.**

This is an **application code issue**, not an infrastructure configuration issue. The infrastructure is now correct, but the application cannot handle the message format being delivered.

---

**Investigation Team:** Automated cloud architecture agents + manual testing
**Total Investigation Time:** ~4 hours
**Infrastructure Fixes:** Complete
**Application Fixes Required:** Lambda code update pending
