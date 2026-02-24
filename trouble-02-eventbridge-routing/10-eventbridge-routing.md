# EventBridge Routing Architecture & Lambda Message Processing

**Date:** 2025-12-30
**Status:** Root Cause Analysis Complete

## Executive Summary

EventBridge routing through SNS introduces message wrapping that breaks Lambdas expecting direct event formats. The core issue is a **message format mismatch**: CloudTrail events wrapped by SNS require unwrapping logic that some Lambdas lack.

**Root Cause:** ManifestIndexer (≤1.65) expects EventBridge format directly but receives SNS-wrapped messages, causing `KeyError: 'detail'` crashes.

---

## The EventBridge → SNS → SQS → Lambda Flow

### Message Transformation Chain

```
S3 Operation (PutObject)
    ↓
CloudTrail logs event (~3-5 min delay)
    ↓
EventBridge rule triggers
    ↓
SNS Topic wraps event in Message field
    ↓
SQS receives SNS notification
    ↓
Lambda must unwrap: SQS → SNS → Event payload
```

### Example Message Structure

**What EventBridge sends to SNS:**

```json
{
  "version": "0",
  "source": "aws.s3",
  "detail": {
    "eventName": "PutObject",
    "s3": {
      "bucket": {"name": "my-bucket"},
      "object": {"key": "file.txt"}
    }
  }
}
```

**What Lambda receives from SQS:**

```json
{
  "Records": [{
    "body": "{\"Type\":\"Notification\",\"Message\":\"{\\\"version\\\":\\\"0\\\",\\\"source\\\":\\\"aws.s3\\\",\\\"detail\\\":{...}}\"}"
  }]
}
```

**Required unwrapping:**

1. Parse `record["body"]` (SQS layer)
2. Parse `body["Message"]` (SNS layer)  ← **Missing in ManifestIndexer ≤1.65**
3. Access `message["detail"]` (EventBridge layer)

---

## Lambda Message Processing Patterns

### Pattern Analysis (From Code Review)

#### ❌ ManifestIndexer (≤1.65) - BROKEN

**File:** [manifest_indexer/\_\_init\_\_.py:254-274](../quilt/lambdas/manifest_indexer/src/t4_lambda_manifest_indexer/__init__.py#L254-L274)

```python
for record in event["Records"]:
    body = orjson.loads(record["body"])  # ✅ Unwraps SQS
    bucket = body["detail"]["s3"]["bucket"]["name"]  # ❌ Expects EventBridge format directly
```

**Problem:** Skips SNS unwrapping step. With EventBridge routing:

- `body` contains `{"Message": "...", "TopicArn": "..."}` (SNS format)
- Accessing `body["detail"]` fails with `KeyError: 'detail'`

**Required Format:** `{"detail": {"s3": {...}}}`
**Unwrapping Layers:** 2 (SQS only)
**Missing:** SNS unwrapping

---

#### ✅ SearchHandler/Indexer - WORKS

**File:** [indexer/index.py:620-785](../quilt/lambdas/indexer/src/t4_lambda_es_indexer/index.py#L620-L785)

```python
for message in event["Records"]:
    body = json.loads(message["body"])                # ✅ Unwraps SQS
    body_message = json.loads(body["Message"])        # ✅ Unwraps SNS
    if "Records" not in body_message:
        logger_.error("No 'Records' key...")
        continue
    events = body_message["Records"]                  # ✅ Expects S3 Records format
```

**Required Format:** `{"Records": [{"s3": {...}}]}`
**Unwrapping Layers:** 3 (SQS → SNS → S3 Records)
**Key Behavior:** Logs error and skips if format doesn't match

---

#### ⚠️ EsIngest - EventBridge Variant

**File:** [es_ingest/\_\_init\_\_.py:73-88](../quilt/lambdas/es_ingest/src/t4_lambda_es_ingest/__init__.py#L73-L88)

```python
(event,) = event["Records"]
event = json.loads(event["body"])  # ✅ Unwraps SQS
bucket = event["detail"]["bucket"]["name"]  # Expects EventBridge (no s3 wrapper)
```

**Required Format:** `{"detail": {"bucket": {...}, "object": {...}}}`
**Unwrapping Layers:** 2 (SQS only)
**Note:** Uses different EventBridge variant without `s3` wrapper in `detail`

---

#### ⚠️ Iceberg - EventBridge Format

**File:** [iceberg/\_\_init\_\_.py:87](../quilt/lambdas/iceberg/src/t4_lambda_iceberg/__init__.py#L87)

```python
event_body = json.loads(record["body"])  # ✅ Unwraps SQS
s3_event = event_body["detail"]["s3"]    # Expects EventBridge format
```

**Required Format:** `{"detail": {"s3": {...}}}`
**Unwrapping Layers:** 2 (SQS only)

---

### Lambda Compatibility Matrix

| Lambda                       | Expected Format     | Unwrapping  | EventBridge (raw)          | EventBridge (transformed)      | S3 Direct |
|------------------------------|---------------------|-------------|----------------------------|--------------------------------|-----------|
| **ManifestIndexer** (≤1.65)  | EventBridge         | SQS only    | ❌ Crashes (no SNS unwrap) | ❌ Crashes (no SNS unwrap)     | N/A       |
| **SearchHandler**            | S3 Records          | SQS → SNS   | ❌ Skips (logs error)      | ✅ Works (with transformer)    | ✅ Works  |
| **EsIngest**                 | EventBridge variant | SQS only    | ⚠️ Untested                | ❌ Wrong format                | N/A       |
| **Iceberg**                  | EventBridge         | SQS only    | ⚠️ Untested                | ❌ Wrong format                | N/A       |

---

## The Two Event Sources Problem

Production environments may have **TWO parallel event sources**, causing confusing test results:

### Flow 1: Direct S3 Notifications (Original)

```
S3 Bucket (S3 Event Notification configured)
    ↓ (instant)
SNS Topic (receives S3 Records format)
    ↓
IndexerQueue
    ↓
SearchHandler ✅ Works
```

### Flow 2: EventBridge Route (New)

```
S3 Bucket
    ↓
CloudTrail (~3-5 min)
    ↓
EventBridge Rule
    ↓
SNS Topic (SAME topic as Flow 1)
    ↓
ManifestIndexerQueue
    ↓
ManifestIndexer ❌ Crashes
```

### Why This Masked the Problem

- **Direct S3 notifications** (Flow 1) → S3 Records format → SearchHandler processes them ✅
- **EventBridge events** (Flow 2) → EventBridge format → SearchHandler skips them (logs error) ❌
- **Result:** Files appear in search, but only from direct S3 notifications
- **Observation:** "It works!" but EventBridge flow actually failing silently

**Critical Testing Requirement:** Disable direct S3 Event Notifications before testing EventBridge routing.

---

## Solutions & Approaches

### Solution 1: Fix Lambda Code (Recommended)

**Add SNS unwrapping to ManifestIndexer:**

```python
for record in event["Records"]:
    body = orjson.loads(record["body"])  # Unwrap SQS

    # NEW: Check if SNS-wrapped
    if "Message" in body:
        body = orjson.loads(body["Message"])  # Unwrap SNS

    bucket = body["detail"]["s3"]["bucket"]["name"]  # Now works!
```

**Benefits:**

- Minimal code change
- Works with EventBridge routing
- Maintains backward compatibility

**Version:** Platform 1.66+

---

### Solution 2: Input Transformers (Limited Use)

**What Input Transformers Do:**

Transform events **BEFORE** SNS wrapping:

```
EventBridge receives CloudTrail event:
{"detail": {"s3": {...}}}
    ↓
[INPUT TRANSFORMER APPLIES HERE]
    ↓
Transformed to S3 Records format:
{"Records": [{"s3": {...}}]}
    ↓
SNS wraps it:
{"Message": "{\"Records\": [...]}", "TopicArn": "..."}
    ↓
Lambda still receives SNS-wrapped message
```

**When Transformers Help:**

- ✅ Converting EventBridge → S3 Records for SearchHandler
- ✅ Adapting event structure for legacy Lambdas expecting S3 format

**When Transformers Are Insufficient:**

- ❌ Cannot solve SNS unwrapping issue
- ❌ Lambda still needs `body["Message"]` unwrapping logic
- ❌ Transformation happens BEFORE SNS wrapping

**Use Case:** Enable SearchHandler to process EventBridge events by transforming them to S3 Records format (which SearchHandler already handles correctly with SNS unwrapping).

---

### Solution 3: Dual Format Support (Comprehensive)

**Enhance all Lambdas to detect and handle multiple formats:**

```python
def unwrap_event(record):
    body = json.loads(record["body"])  # Unwrap SQS

    # Unwrap SNS if present
    if "Message" in body:
        body = json.loads(body["Message"])

    # Detect format
    if "Records" in body:
        # S3 Records format (direct S3 or transformed EventBridge)
        return body["Records"][0]["s3"]
    elif "detail" in body:
        # EventBridge format
        if "s3" in body["detail"]:
            return body["detail"]["s3"]
        else:
            return body["detail"]  # Variant format
    else:
        raise ValueError(f"Unknown event format: {body.keys()}")
```

**Benefits:**

- Handles all event sources (S3 direct, EventBridge, EventBridge with transformer)
- Graceful migration path
- No infrastructure changes required

**Version:** Platform 1.66+

---

## Testing Strategy

### Critical Testing Principle

**ALWAYS isolate event sources during testing to avoid false positives.**

### Test Environment Setup

**Prerequisites:**

1. Fresh test bucket with NO existing S3 Event Notifications
2. CloudTrail enabled for S3 data events
3. New SNS topic (not shared with other event sources)
4. New SQS queues for each Lambda
5. EventBridge rule targeting the new SNS topic

---

### Test 1: Baseline - Direct S3 Notifications

**Purpose:** Verify Lambdas work with standard S3 notifications

**Setup:**

1. Configure S3 bucket → SNS → SQS → Lambda (NO EventBridge)
2. Upload test file to S3
3. Verify Lambda processes S3 Records format

**Expected:**

- ✅ SearchHandler: Processes S3 Records
- ✅ Files indexed within 2 minutes

**Validation:**

- [ ] Files appear in search UI
- [ ] CloudWatch Logs show successful processing
- [ ] No error messages

---

### Test 2: EventBridge WITHOUT Input Transformer

**Purpose:** Verify which Lambdas handle raw EventBridge events

**Setup:**

1. ⚠️ **CRITICAL:** Remove direct S3 Event Notification
2. Configure EventBridge rule → SNS (NO Input Transformer)
3. Subscribe queues to SNS topic
4. Upload test file to S3
5. Wait 3-5 minutes for CloudTrail

**Expected Results:**

| Lambda                      | Expected Behavior                          | Pass Criteria              |
|-----------------------------|--------------------------------------------|----------------------------|
| **ManifestIndexer** (≤1.65) | ❌ Crashes with `KeyError: 'detail'`       | CloudWatch shows errors    |
| **ManifestIndexer** (≥1.66) | ✅ Processes EventBridge format            | Package appears in catalog |
| **SearchHandler**           | ❌ Skips events (logs "No 'Records' key") | CloudWatch shows errors    |

**Critical Validation:**

- [ ] EventBridge rule state is ENABLED
- [ ] EventBridge triggered (CloudWatch Metrics: TriggeredRules > 0)
- [ ] SNS published messages (NumberOfMessagesPublished > 0)
- [ ] Lambda invoked (Invocations > 0)
- [ ] Check CloudWatch Logs for EACH Lambda
- [ ] Verify NO packages indexed (ManifestIndexer ≤1.65)

---

### Test 3: EventBridge WITH Input Transformer

**Purpose:** Verify Input Transformer enables SearchHandler

**Setup:**

1. Same as Test 2, but ADD Input Transformer to EventBridge rule
2. Transformer converts EventBridge → S3 Records format
3. Upload test file to S3
4. Wait 3-5 minutes for CloudTrail

**Expected Results:**

| Lambda                      | Expected Behavior                                     | Pass Criteria           |
|-----------------------------|-------------------------------------------------------|-------------------------|
| **ManifestIndexer** (≤1.65) | ❌ Still crashes (transformer doesn't fix SNS unwrap) | CloudWatch shows errors |
| **SearchHandler**           | ✅ Processes S3 Records format                        | Files indexed           |

**Critical Validation:**

- [ ] SearchHandler processes events (no "No 'Records' key" errors)
- [ ] Files appear in search
- [ ] Packages still NOT indexed (ManifestIndexer still broken in ≤1.65)

---

### Test 4: Platform 1.66 with SNS Unwrap Fix

**Purpose:** Verify SNS unwrapping fix resolves ManifestIndexer issue

**Setup:**

1. Deploy ManifestIndexer 1.66 with SNS unwrapping
2. EventBridge WITHOUT Input Transformer
3. Upload test file
4. Wait 3-5 minutes

**Expected Results:**

- ✅ ManifestIndexer processes EventBridge format
- ✅ Package appears in catalog
- ⚠️ SearchHandler still needs Input Transformer

---

## Managing S3 Event Notifications

### Why Disable Direct S3 Notifications During Testing

**Problems with mixed event sources:**

1. **Duplicate Events** - Same S3 operation triggers both flows
2. **Confusing Test Results** - Success may come from direct notifications, masking EventBridge failures
3. **Mixed Message Formats** - Same queue receives both S3 Records and EventBridge formats

### Check for Existing S3 Event Notifications

**Via AWS CLI:**

```bash
aws s3api get-bucket-notification-configuration \
  --bucket your-bucket-name \
  --region us-east-1

# Expected output if notifications exist:
# {
#   "TopicConfigurations": [
#     {
#       "Id": "...",
#       "TopicArn": "arn:aws:sns:...",
#       "Events": ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]
#     }
#   ]
# }

# Expected output if no notifications:
# {}
```

### Disable S3 Event Notifications

**Save backup first:**

```bash
aws s3api get-bucket-notification-configuration \
  --bucket your-bucket-name \
  --region us-east-1 \
  > s3-notification-backup.json
```

**Remove notifications:**

```bash
aws s3api put-bucket-notification-configuration \
  --bucket your-bucket-name \
  --notification-configuration '{}' \
  --region us-east-1
```

**Verify removal:**

```bash
aws s3api get-bucket-notification-configuration \
  --bucket your-bucket-name \
  --region us-east-1
# Should return: {}
```

### Restore S3 Event Notifications

```bash
aws s3api put-bucket-notification-configuration \
  --bucket your-bucket-name \
  --notification-configuration file://s3-notification-backup.json \
  --region us-east-1
```

---

## Common Testing Mistakes

### ❌ Mistake 1: Relying on Intermediate Metrics

**Bad:**
- EventBridge triggered ✅
- SNS published ✅
- SQS received ✅
- **Conclusion:** "It works!"

**Problem:** Lambda may be crashing! Always check final output.

**Good:**
- Check CloudWatch Logs for Lambda errors
- Verify data appears in final destination (UI, database)
- Test actual user workflow (search for file, view package)

---

### ❌ Mistake 2: Not Isolating Event Sources

**Bad:**
- Leave direct S3 Event Notifications enabled
- Add EventBridge routing
- Test by uploading files
- **Conclusion:** "It works!" (but via S3 notifications, not EventBridge)

**Good:**
- Remove direct S3 Event Notifications before testing EventBridge
- Or use separate test bucket
- Verify events come from EventBridge by checking message format in logs

---

### ❌ Mistake 3: Not Waiting for CloudTrail

**Bad:**
- Upload file
- Wait 10 seconds
- No events
- **Conclusion:** "EventBridge is broken!"

**Good:**
- Wait 3-5 minutes for CloudTrail to log events
- Check CloudTrail Event History to verify S3 event logged
- Then check EventBridge metrics

---

### ❌ Mistake 4: Assuming Lambda Success from Invocation Count

**Bad:**
- Lambda invoked 10 times ✅
- **Conclusion:** "Lambda is processing events!"

**Good:**
- Check Lambda Errors metric (should be 0)
- Check Lambda Duration (abnormally short = crash)
- Read CloudWatch Logs to verify actual processing

---

## Production Deployment Recommendations

### When EventBridge is Primary Event Source

**Recommended Configuration:**

- ✅ EventBridge rule ENABLED
- ❌ Direct S3 Event Notifications REMOVED
- ✅ Input Transformer configured (if needed for Platform ≤1.65)

**Benefits:**

- Single source of truth for events
- Easier debugging (one event flow)
- No duplicate processing
- Consistent message format

**Tradeoffs:**

- ~3-5 minute delay for CloudTrail logging
- Dependency on CloudTrail availability

---

### Version-Specific Recommendations

#### Platform ≤1.65 (Current)

**Required Configuration:**

- ✅ EventBridge rule with Input Transformer (for SearchHandler)
- ❌ ManifestIndexer will NOT work with EventBridge routing
- ⚠️ Must use direct S3 notifications for ManifestIndexer OR upgrade to 1.66

---

#### Platform 1.66 (With SNS Unwrap Fix)

**Required Configuration:**

- ✅ EventBridge rule (Input Transformer optional but recommended)
- ✅ ManifestIndexer works WITHOUT Input Transformer
- ✅ SearchHandler needs Input Transformer OR dual format support

---

#### Platform 1.66+ (With Dual Format Support)

**Required Configuration:**

- ✅ EventBridge rule (Input Transformer optional)
- ✅ ALL Lambdas work with OR without Input Transformer
- ✅ System handles mixed event sources gracefully

---

## Quick Reference Commands

### Verification Commands

```bash
# Check EventBridge rule state
aws events describe-rule \
  --name your-eventbridge-rule \
  --region us-east-1 \
  --query 'State' \
  --output text
# Output: ENABLED or DISABLED

# Check S3 event notifications
aws s3api get-bucket-notification-configuration \
  --bucket your-bucket-name \
  --region us-east-1
# Output: {} (none) or {...} (configured)

# Check CloudTrail events
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=your-bucket-name \
  --max-results 5 \
  --region us-east-1

# Check EventBridge metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Events \
  --metric-name TriggeredRules \
  --dimensions Name=RuleName,Value=your-rule-name \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --region us-east-1
```

---

## Conclusion

**Core Problem:** EventBridge routing through SNS creates a message wrapping layer that breaks Lambdas expecting direct event formats.

**Root Cause:** ManifestIndexer (≤1.65) lacks SNS unwrapping logic, causing crashes when receiving EventBridge events routed through SNS.

**Solution Path:**

1. **Platform 1.66:** Add SNS unwrapping to ManifestIndexer (minimal fix)
2. **Platform 1.66+:** Add dual format support to all Lambdas (comprehensive fix)
3. **Testing:** Always isolate event sources and check CloudWatch Logs, not just metrics

**Key Insight:** Input Transformers are useful for format conversion but cannot solve the SNS unwrapping issue. Lambda code fixes are required for reliable EventBridge routing.
