# Input Transformer Hypothesis & Testing Strategy

**Date:** 2025-12-30
**Status:** Analysis Complete - Lambda Code Verified

## Executive Summary

Input Transformers are **insufficient** to solve the EventBridge routing issue because they transform events BEFORE SNS wrapping. The core issue is that Lambdas must unwrap SNS messages regardless of transformation, and some Lambdas (ManifestIndexer in ≤1.65) lack SNS unwrapping logic.

---

## Lambda Message Processing Patterns

### Current Lambda Implementations (Verified from Code)

#### 1. ManifestIndexer (≤1.65) - BROKEN ❌

**File:** `/Users/ernest/GitHub/quilt/lambdas/manifest_indexer/src/t4_lambda_manifest_indexer/__init__.py:254-274`

**Pattern:**
```python
for record in event["Records"]:
    body = orjson.loads(record["body"])  # ✅ Unwraps SQS
    bucket = body["detail"]["s3"]["bucket"]["name"]  # ❌ Expects EventBridge format directly
```

**Expected Format:** `{"detail": {"s3": {"bucket": {...}, "object": {...}}}}`
**Unwrapping:** SQS only (1 layer)
**Problem:** Assumes `body["detail"]` exists, but SNS wraps it in `body["Message"]`

---

#### 2. SearchHandler/Indexer - WORKS ✅

**File:** `/Users/ernest/GitHub/quilt/lambdas/indexer/src/t4_lambda_es_indexer/index.py:620-785`

**Pattern:**
```python
for message in event["Records"]:
    body = json.loads(message["body"])                # ✅ Unwraps SQS
    body_message = json.loads(body["Message"])        # ✅ Unwraps SNS
    if "Records" not in body_message:
        logger_.error("No 'Records' key...")
        continue
    events = body_message["Records"]                  # ✅ Expects S3 Records format
```

**Expected Format:** `{"Records": [{"s3": {"bucket": {...}, "object": {...}}}]}`
**Unwrapping:** SQS → SNS → S3 Records (3 layers)
**Key Behavior:** Logs error and skips if "Records" not found

---

#### 3. EsIngest - EventBridge Format ✅

**File:** `/Users/ernest/GitHub/quilt/lambdas/es_ingest/src/t4_lambda_es_ingest/__init__.py:73-88`

**Pattern:**
```python
(event,) = event["Records"]
event = json.loads(event["body"])  # ✅ Unwraps SQS
bucket = event["detail"]["bucket"]["name"]  # Expects EventBridge (no s3 wrapper)
```

**Expected Format:** `{"detail": {"bucket": {...}, "object": {...}}}`
**Unwrapping:** SQS only (1 layer)
**Note:** Uses different EventBridge variant (no `s3` wrapper in `detail`)

---

#### 4. Iceberg - EventBridge Format ✅

**File:** `/Users/ernest/GitHub/quilt/lambdas/iceberg/src/t4_lambda_iceberg/__init__.py:87`

**Pattern:**
```python
event_body = json.loads(record["body"])  # ✅ Unwraps SQS
s3_event = event_body["detail"]["s3"]    # Expects EventBridge format
```

**Expected Format:** `{"detail": {"s3": {"bucket": {...}, "object": {...}}}}`
**Unwrapping:** SQS only (1 layer)

---

### Summary Table

| Lambda | Expected Format | Unwrapping | EventBridge (no transformer) | S3 Records (with transformer) |
|--------|----------------|------------|------------------------------|------------------------------|
| **ManifestIndexer** (≤1.65) | EventBridge | SQS only | ❌ Crashes (no SNS unwrap) | ❌ Crashes (no SNS unwrap) |
| **SearchHandler** | S3 Records | SQS → SNS | ❌ Skips (logs error) | ✅ Works |
| **EsIngest** | EventBridge variant | SQS only | ⚠️ Unknown (needs testing) | ❌ Wrong format |
| **Iceberg** | EventBridge | SQS only | ⚠️ Unknown (needs testing) | ❌ Wrong format |

---

## Input Transformer Analysis

### What Input Transformers Do

**Transform BEFORE SNS wrapping:**

```
EventBridge receives CloudTrail event:
{"source": "aws.s3", "detail": {"eventName": "PutObject", ...}}
    ↓
[INPUT TRANSFORMER APPLIES HERE]
    ↓
Transformed to S3 Records format:
{"Records": [{"s3": {"bucket": {...}, "object": {...}}}]}
    ↓
SNS wraps it:
{"Message": "{\"Records\": [...]}", "TopicArn": "..."}
    ↓
SQS wraps SNS message:
{"Records": [{"body": "{\"Message\": ...}"}]}
    ↓
Lambda receives: SQS → SNS → Transformed Event (3 layers)
```

**Key Insight:** Input Transformer changes the innermost payload, but SNS/SQS wrapping is unchanged.

---

### When Input Transformers Are...

#### NECESSARY ✅

**Scenario:** SearchHandler Lambda receiving EventBridge events

- SearchHandler expects S3 Records format: `{"Records": [{"s3": {...}}]}`
- EventBridge sends: `{"detail": {"s3": {...}}}`
- Without transformer: SearchHandler logs "No 'Records' key" and skips

**Solution:** Input Transformer converts EventBridge → S3 Records format

---

#### UNNECESSARY ❌

**Scenario:** ManifestIndexer Lambda with SNS unwrapping (≥1.66)

- ManifestIndexer expects EventBridge format: `{"detail": {"s3": {...}}}`
- EventBridge sends: `{"detail": {"s3": {...}}}`
- With SNS unwrapping: ManifestIndexer can extract EventBridge format directly

**No transformation needed** - raw EventBridge format matches expectations

---

#### INSUFFICIENT ⚠️

**Scenario:** ManifestIndexer Lambda without SNS unwrapping (≤1.65)

- Input Transformer converts: EventBridge → S3 Records
- SNS wraps: `{"Message": "{\"Records\": [...]}"}`
- ManifestIndexer tries: `body["detail"]` ❌ Crashes
- **Problem:** Lambda still needs to unwrap `body["Message"]` first

**Input Transformer alone cannot solve this** - Lambda code fix required

---

## The Two Event Sources Problem

### Why Testing Was Flaky

Production environments may have **TWO parallel event sources**:

#### Flow 1: Direct S3 Notifications (Original)
```
S3 Bucket (S3 Event Notification configured)
    ↓
SNS Topic (receives S3 Records format)
    ↓
IndexerQueue
    ↓
SearchHandler ✅ Works
```

#### Flow 2: EventBridge Route (New)
```
S3 Bucket
    ↓
CloudTrail
    ↓
EventBridge Rule (no Input Transformer)
    ↓
SNS Topic (SAME topic as Flow 1)
    ↓
ManifestIndexerQueue
    ↓
ManifestIndexer ❌ Crashes
```

### Why SearchHandler Appeared to Work

- **Direct S3 notifications** (Flow 1) → S3 Records format → SearchHandler processes them ✅
- **EventBridge events** (Flow 2) → EventBridge format → SearchHandler skips them (logs error) ❌
- **Result:** Files appear in search, but only from direct S3 notifications

**This masked the EventBridge routing issue!**

---

## Rigorous End-to-End Testing Strategy

### Test Environment Setup

**Goal:** Isolate EventBridge flow from direct S3 notifications

#### Prerequisites
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
- ✅ ManifestIndexer: N/A (receives from different queue)

**Pass Criteria:** Files indexed within 2 minutes

---

### Test 2: EventBridge WITHOUT Input Transformer

**Purpose:** Verify which Lambdas handle raw EventBridge events

**Setup:**
1. Remove direct S3 Event Notification
2. Configure EventBridge rule → SNS (NO Input Transformer)
3. Subscribe queues to SNS topic
4. Upload test file to S3

**Expected Results:**

| Lambda | Expected Behavior | Pass Criteria |
|--------|------------------|---------------|
| **ManifestIndexer** (≤1.65) | ❌ Crashes with `KeyError: 'detail'` | CloudWatch shows errors |
| **ManifestIndexer** (≥1.66) | ✅ Processes EventBridge format | Package appears in catalog |
| **SearchHandler** | ❌ Skips events (logs "No 'Records' key") | CloudWatch shows errors |
| **EsIngest** | ⚠️ Unknown | Check CloudWatch logs |
| **Iceberg** | ⚠️ Unknown | Check CloudWatch logs |

**Critical Validation:**
- Check CloudWatch Logs for EACH Lambda
- Verify NO packages indexed (ManifestIndexer ≤1.65)
- Verify SearchHandler logs errors, not successes

---

### Test 3: EventBridge WITH Input Transformer

**Purpose:** Verify Input Transformer enables SearchHandler

**Setup:**
1. Same as Test 2, but ADD Input Transformer to EventBridge rule
2. Input Transformer converts EventBridge → S3 Records format
3. Upload test file to S3

**Expected Results:**

| Lambda | Expected Behavior | Pass Criteria |
|--------|------------------|---------------|
| **ManifestIndexer** (≤1.65) | ❌ Still crashes (S3 Records format doesn't help) | CloudWatch shows errors |
| **ManifestIndexer** (≥1.66) | ⚠️ May fail (expects EventBridge, gets S3 Records) | Check CloudWatch logs |
| **SearchHandler** | ✅ Processes S3 Records format | Files indexed |
| **EsIngest** | ❌ Fails (expects EventBridge variant) | CloudWatch shows errors |
| **Iceberg** | ❌ Fails (expects EventBridge) | CloudWatch shows errors |

**Critical Validation:**
- SearchHandler MUST process events (no "No 'Records' key" errors)
- Files MUST appear in search
- Packages MUST NOT appear (ManifestIndexer still broken in ≤1.65)

---

### Test 4: Dual Format Support (≥1.66 with enhanced fix)

**Purpose:** Verify Lambdas handle BOTH EventBridge and S3 Records formats

**Setup:**
1. Same as Test 3 (EventBridge with Input Transformer)
2. Deploy enhanced Lambdas with dual format detection
3. Upload test file to S3

**Expected Results:**

| Lambda | Expected Behavior | Pass Criteria |
|--------|------------------|---------------|
| **ManifestIndexer** | ✅ Handles both formats | Package indexed |
| **SearchHandler** | ✅ Handles both formats | Files indexed |
| **EsIngest** | ✅ Handles both formats | Objects in Elasticsearch |
| **Iceberg** | ✅ Handles both formats | Iceberg tables updated |

**Critical Validation:**
- ALL Lambdas process events successfully
- NO errors in CloudWatch Logs
- End-to-end flow works (upload → indexed within 3 minutes)

---

### Test 5: Chaos - Mixed Event Sources

**Purpose:** Verify system handles both direct S3 and EventBridge events

**Setup:**
1. Enable BOTH direct S3 Event Notification AND EventBridge
2. Upload test files to trigger both flows
3. Verify no duplicate processing

**Expected Results:**
- ✅ Lambdas handle both event formats
- ⚠️ May see duplicate events (need deduplication logic)
- ✅ Final state correct (no data corruption)

**Critical Validation:**
- Check for duplicate processing
- Verify idempotency (same file processed twice = same result)

---

## Validation Checklist

For EACH test, verify:

### Infrastructure Layer
- [ ] EventBridge rule state is ENABLED
- [ ] EventBridge rule triggered (CloudWatch Metrics: TriggeredRules > 0)
- [ ] SNS topic received messages (CloudWatch Metrics: NumberOfMessagesPublished > 0)
- [ ] SQS queues received messages (CloudWatch Metrics: NumberOfMessagesReceived > 0)
- [ ] Lambda invoked (CloudWatch Metrics: Invocations > 0)

### Application Layer
- [ ] Lambda completed successfully (CloudWatch Metrics: Errors = 0)
- [ ] CloudWatch Logs show expected processing (no "No 'Records' key" errors)
- [ ] Final data state correct (files/packages appear in UI)

### Timing Validation
- [ ] CloudTrail event logged (wait ~3 minutes for CloudTrail)
- [ ] EventBridge triggered within 1 minute of CloudTrail event
- [ ] Lambda processed within 30 seconds of SQS message
- [ ] Total latency: Upload → Indexed < 5 minutes

---

## Critical Testing Mistakes to Avoid

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
- Verify events come from EventBridge by checking message format

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

### ❌ Mistake 5: Testing Different Workflows

**Bad:**
- Test file uploads (object indexing)
- **Conclusion:** "EventBridge works!"
- **Problem:** Package indexing may still be broken

**Good:**
- Test file uploads AND package creation
- Test delete operations
- Test edge cases (large files, special characters, etc.)

---

## Version-Specific Testing

### Platform ≤1.65 (Current)

**Expected Failures:**
- ❌ ManifestIndexer crashes with EventBridge routing (no SNS unwrap)
- ⚠️ SearchHandler skips EventBridge events (expects S3 Records)

**Test Focus:**
- Verify failures occur as expected
- Document error messages for users
- Confirm Input Transformer enables SearchHandler

---

### Platform 1.66 (With SNS Unwrap Fix)

**Expected Behavior:**
- ✅ ManifestIndexer works WITHOUT Input Transformer (handles EventBridge format)
- ⚠️ SearchHandler still needs Input Transformer (expects S3 Records)

**Test Focus:**
- Verify ManifestIndexer processes raw EventBridge events
- Confirm Input Transformer still needed for SearchHandler
- Document: "Input Transformer required for full functionality"

---

### Platform 1.66+ (With Dual Format Support)

**Expected Behavior:**
- ✅ ALL Lambdas work with OR without Input Transformer
- ✅ System handles mixed event sources

**Test Focus:**
- Test with Input Transformer enabled
- Test with Input Transformer disabled
- Verify both configurations work identically
- Document: "Input Transformer optional in 1.66+"

---

## Managing S3 Event Notifications

### Why You Need to Disable Direct S3 Notifications

When migrating to EventBridge routing, you MUST disable or remove direct S3 Event Notifications to avoid:

1. **Duplicate Events** - Same S3 operation triggers both direct notification AND EventBridge
2. **Confusing Test Results** - Success may come from direct notifications, masking EventBridge failures
3. **Mixed Message Formats** - Same queue receives both S3 Records (direct) and EventBridge formats
4. **Resource Waste** - Processing same event twice

**AWS Limitation:** S3 buckets can only have ONE event notification configuration, but EventBridge events don't count against this limit. You can have BOTH enabled, which causes the problems above.

---

### How to Check for Existing S3 Event Notifications

**Via AWS Console:**
1. Go to **S3 Console** → Select your bucket
2. Click **Properties** tab
3. Scroll to **Event notifications** section
4. Look for existing notification configurations

**Via AWS CLI:**
```bash
# Check for event notification configuration
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

---

### How to Disable S3 Event Notifications

**Option A: Remove Notification Configuration (Recommended for Testing)**

**Via AWS Console:**
1. Go to **S3 Console** → Select your bucket → **Properties**
2. Scroll to **Event notifications**
3. Select the notification configuration
4. Click **Delete**

**Via AWS CLI:**
```bash
# Save current configuration first (backup)
aws s3api get-bucket-notification-configuration \
  --bucket your-bucket-name \
  --region us-east-1 \
  > s3-notification-backup.json

# Remove all event notifications
aws s3api put-bucket-notification-configuration \
  --bucket your-bucket-name \
  --notification-configuration '{}' \
  --region us-east-1

# Verify removal
aws s3api get-bucket-notification-configuration \
  --bucket your-bucket-name \
  --region us-east-1
# Should return: {}
```

**Option B: Modify Notification to Use Different Prefix (Coexistence)**

If you need BOTH direct S3 notifications AND EventBridge (not recommended):

```bash
# Modify notification to only trigger for specific prefix
aws s3api put-bucket-notification-configuration \
  --bucket your-bucket-name \
  --notification-configuration '{
    "TopicConfigurations": [
      {
        "Id": "direct-notifications-legacy-only",
        "TopicArn": "arn:aws:sns:us-east-1:123456789012:legacy-topic",
        "Events": ["s3:ObjectCreated:*"],
        "Filter": {
          "Key": {
            "FilterRules": [
              {
                "Name": "prefix",
                "Value": "legacy/"
              }
            ]
          }
        }
      }
    ]
  }' \
  --region us-east-1
```

**Now:**
- Files in `s3://bucket/legacy/*` → Direct S3 notification
- Files elsewhere → Only EventBridge
- **Still risky:** Easy to upload to wrong location

---

### How to Restore S3 Event Notifications

**Via AWS CLI:**
```bash
# Restore from backup
aws s3api put-bucket-notification-configuration \
  --bucket your-bucket-name \
  --notification-configuration file://s3-notification-backup.json \
  --region us-east-1
```

---

### Testing Strategy: When to Disable/Enable

#### Phase 1: Testing EventBridge in Isolation
**Goal:** Verify EventBridge routing works independently

1. **Before testing:**
   - ✅ Disable/remove direct S3 Event Notifications
   - ✅ Verify configuration is empty (`{}`)

2. **Test EventBridge:**
   - Upload files → Should ONLY trigger EventBridge flow
   - Check CloudWatch Logs to confirm EventBridge event format

3. **Expected behavior:**
   - ✅ Events come through EventBridge → SNS → SQS → Lambda
   - ❌ No direct S3 notification events

#### Phase 2: Testing Direct S3 Notifications (Baseline)
**Goal:** Verify Lambdas work with traditional S3 notifications

1. **Before testing:**
   - ✅ Disable EventBridge rule (`aws events disable-rule`)
   - ✅ Re-enable direct S3 Event Notifications

2. **Test S3 notifications:**
   - Upload files → Should ONLY trigger direct S3 flow
   - Verify S3 Records format in CloudWatch Logs

3. **Expected behavior:**
   - ✅ Events come directly from S3 → SNS → SQS → Lambda
   - ❌ No EventBridge events

#### Phase 3: Production Deployment
**Goal:** Use EventBridge as primary, disable legacy S3 notifications

1. **Deployment order:**
   - ✅ Deploy Lambda fixes (SNS unwrapping, dual format support)
   - ✅ Enable EventBridge rule
   - ✅ Test with small traffic
   - ✅ **Once validated:** Remove direct S3 Event Notifications
   - ⚠️ Keep backup of S3 notification config (rollback plan)

2. **Rollback plan (if EventBridge fails):**
   - ❌ Disable EventBridge rule
   - ✅ Restore S3 Event Notifications from backup
   - ✅ Verify direct S3 flow working

---

### Production Considerations

#### When EventBridge is Primary Event Source

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
- Slightly higher complexity

---

#### When Direct S3 Notifications are Primary

**Recommended Configuration:**
- ❌ EventBridge rule DISABLED (or use different bucket)
- ✅ Direct S3 Event Notifications ENABLED
- ⚠️ Cannot use EventBridge routing features

**Benefits:**
- Near real-time event delivery (<1 second)
- No CloudTrail dependency
- Simpler architecture

**Limitations:**
- Cannot share events with other AWS services (FSx, etc.)
- S3's "one notification config" limitation applies

---

#### Hybrid Approach (Not Recommended)

**If you MUST have both:**
- Use prefix-based filtering on direct S3 notifications
- EventBridge captures all events, direct S3 captures subset
- High risk of duplicate processing
- Complex debugging

**Better Alternative:**
- Use EventBridge as primary
- Add filtering in EventBridge rules instead of S3 prefixes
- Single event source, better control

---

## Recommended Testing Order

1. **Test 2 first** (EventBridge WITHOUT Input Transformer)
   - ⚠️ **Disable S3 Event Notifications before testing**
   - Fastest to set up
   - Reveals Lambda format expectations
   - Confirms SNS unwrapping issue

2. **Test 3 next** (EventBridge WITH Input Transformer)
   - ⚠️ **Keep S3 Event Notifications disabled**
   - Shows which Lambdas benefit from transformation
   - Reveals format incompatibilities

3. **Test 1 for baseline** (Direct S3 Notifications)
   - ⚠️ **Disable EventBridge rule, enable S3 notifications**
   - Confirms Lambdas work in known-good configuration
   - Provides reference for comparison

4. **Test 4 after fix** (Dual Format Support)
   - ⚠️ **Disable S3 Event Notifications, enable EventBridge**
   - Validates fix works for both formats
   - Confirms no regressions

5. **Test 5 last** (Mixed Event Sources)
   - ⚠️ **Only if you need to validate coexistence**
   - Most complex scenario
   - Only test after individual flows work
   - Verify deduplication logic

---

## Quick Reference: Commands

### Save Current Configuration
```bash
# Backup S3 event notifications
aws s3api get-bucket-notification-configuration \
  --bucket your-bucket-name \
  --region us-east-1 \
  > s3-notification-backup.json

# Backup EventBridge rule
aws events describe-rule \
  --name your-eventbridge-rule \
  --region us-east-1 \
  > eventbridge-rule-backup.json
```

### Disable for Testing
```bash
# Disable EventBridge rule (keeps configuration)
aws events disable-rule \
  --name your-eventbridge-rule \
  --region us-east-1

# Remove S3 event notifications
aws s3api put-bucket-notification-configuration \
  --bucket your-bucket-name \
  --notification-configuration '{}' \
  --region us-east-1
```

### Enable After Testing
```bash
# Enable EventBridge rule
aws events enable-rule \
  --name your-eventbridge-rule \
  --region us-east-1

# Restore S3 event notifications
aws s3api put-bucket-notification-configuration \
  --bucket your-bucket-name \
  --notification-configuration file://s3-notification-backup.json \
  --region us-east-1
```

### Verify Current State
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
```

---

## Conclusion

**Key Findings:**

1. **Input Transformers are insufficient** because they transform BEFORE SNS wrapping
2. **Lambda code fixes are required** to unwrap SNS messages
3. **Testing must isolate event sources** to avoid false positives
4. **Multiple Lambdas have different format expectations** requiring careful analysis

**Path Forward:**

- **Platform 1.66:** Add SNS unwrapping to ManifestIndexer (minimal fix)
- **Platform 1.66+:** Add dual format support to all Lambdas (complete fix)
- **Documentation:** Update EventBridge guide to reflect version-specific requirements

**Testing Strategy:**

- Always check CloudWatch Logs, not just metrics
- Isolate event sources during testing
- Test end-to-end workflows, not just individual components
- Validate both success AND failure cases
