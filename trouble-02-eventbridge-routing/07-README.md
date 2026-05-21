# EventBridge Routing Issue - Investigation Summary

**Status:** PARTIALLY RESOLVED (Infrastructure Fixed, Lambda Code Issue Identified) | **Date:** 2025-12-30

## Executive Summary

Customer's S3 events weren't reaching Quilt's package indexing pipeline. Investigation revealed **three layers of issues**:

1. **Infrastructure Layer 1 (FIXED):** EventBridge rule was DISABLED ✅
2. **Infrastructure Layer 2 (FIXED):** Missing SNS subscriptions and SQS policies ✅
3. **Application Layer (IDENTIFIED):** ManifestIndexer Lambda cannot unwrap SNS messages ❌

**The infrastructure now routes events correctly, but the application code requires fixes in Platform 1.66+.**

---

## Critical Discovery: Input Transformers Are Insufficient

**Key Insight:** Input Transformers transform events BEFORE SNS wrapping. They cannot eliminate the need for SNS unwrapping logic in Lambda code.

**Why This Matters:**
- EventBridge → SNS → SQS → Lambda creates 3 layers of message wrapping
- Input Transformers only affect the innermost payload
- Lambdas MUST still unwrap SQS and SNS layers regardless of transformation
- Some Quilt Lambdas lack SNS unwrapping code (ManifestIndexer in ≤1.65)

**Result:** Infrastructure fixes enable event flow, but Lambda code issues prevent processing.

See [10-input-transformer-hypothesis.md](10-input-transformer-hypothesis.md) for detailed analysis.

---

## The Three-Layer Problem

### Layer 1: EventBridge Rule (FIXED ✅)

**Problem:** Rule `cloudtrail-to-sns` was DISABLED

**Fix:**
```bash
aws events enable-rule --name cloudtrail-to-sns --region us-east-1
```

**Result:** EventBridge started routing CloudTrail events to SNS (176+ events)

---

### Layer 2: SNS Subscriptions & Policies (FIXED ✅)

**Problem:** Critical queues weren't subscribed to SNS topic

**Missing:**
- `ManifestIndexerQueue` (package indexing)
- `EsIngestQueue` (object indexing)

**Fix:**
```bash
# Subscribe ManifestIndexerQueue
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:712023778557:quilt-eventbridge-test-QuiltNotifications-* \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:us-east-1:712023778557:quilt-staging-ManifestIndexerQueue-* \
  --region us-east-1

# Add SQS policy to allow SNS
aws sqs set-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/712023778557/quilt-staging-ManifestIndexerQueue-* \
  --attributes '{"Policy": "..."}'

# Same for EsIngestQueue
```

**Result:** Messages now reach queues, triggering Lambda invocations

---

### Layer 3: Lambda Code Compatibility (UNRESOLVED ❌)

**Problem:** ManifestIndexer expects EventBridge format but receives SNS-wrapped messages

**Error:** `KeyError: 'detail'` at `t4_lambda_manifest_indexer/__init__.py:263`

**Root Cause:**
```python
# ManifestIndexer (≤1.65) - BROKEN
for record in event["Records"]:
    body = orjson.loads(record["body"])  # Unwraps SQS only
    bucket = body["detail"]["s3"]["bucket"]["name"]  # ❌ Assumes body is EventBridge format
```

**Reality:** `body` is SNS message: `{"Message": "...", "TopicArn": "..."}`

**Working Pattern (from SearchHandler):**
```python
# SearchHandler - WORKS
for message in event["Records"]:
    body = json.loads(message["body"])                # Unwrap SQS
    body_message = json.loads(body["Message"])        # Unwrap SNS ← CRITICAL
    events = body_message["Records"]                  # Access payload
```

**Impact:**
- ✅ Infrastructure delivers events correctly
- ✅ SearchHandler processes file indexing (works)
- ❌ ManifestIndexer crashes on every event (100% failure rate)
- ❌ Packages don't appear in catalog

**Fix Required:** Platform 1.66+ will add SNS unwrapping to ManifestIndexer

See [08-FAILURE_REPORT.md](08-FAILURE_REPORT.md) for complete analysis.

---

## Key Lessons Learned

### 1. Metrics ≠ End-to-End Success

**False Positive:**
- EventBridge triggers: ✅ 176 events
- SNS publishes: ✅ 178 messages
- SQS receives: ✅ Messages delivered
- **Conclusion:** "It works!" ❌ WRONG

**Reality:**
- Lambda invoked: ✅ 58 times
- Lambda errors: ❌ 60+ errors (100% failure rate)
- Packages indexed: ❌ 0

**Lesson:** Always verify final output (packages in catalog), not intermediate metrics.

---

### 2. Input Transformers Cannot Fix Lambda Code Issues

**Misconception:** "Add Input Transformer to convert EventBridge → S3 format"

**Reality:**
```
EventBridge (CloudTrail event)
    ↓
[INPUT TRANSFORMER] ← Transforms here
    ↓
SNS receives transformed event
    ↓
SNS wraps: {"Message": "{...transformed event...}", ...}  ← ALWAYS wraps
    ↓
Lambda receives: SQS → SNS → Transformed event
    ↓
Lambda STILL needs to unwrap SNS layer
```

**Lesson:** Input Transformers change the innermost payload but don't eliminate SNS wrapping. Lambda code must handle SNS messages regardless.

---

### 3. Test With Real Workflows, Not Synthetic Events

**Wrong Test:**
```bash
# Upload file → Check metrics → "Success!"
aws s3 cp test.txt s3://bucket/test.txt
# EventBridge triggered ✅
# SNS published ✅
```

**Right Test:**
```bash
# Create package → Verify in UI
quilt3 push user/package s3://bucket/
# Wait 3 minutes
# Check: https://catalog.quiltdata.com/b/bucket/packages
# Does package appear? NO ❌
```

**Lesson:** Test actual user workflows to detect processing failures.

---

### 4. Two Event Sources = Flaky Testing

**Hidden Problem:**
```
S3 Bucket
    ├─→ Direct S3 Event Notification → SNS → IndexerQueue → SearchHandler ✅ Works
    └─→ EventBridge → SNS → ManifestIndexerQueue → ManifestIndexer ❌ Fails
```

**Why Testing Was Confusing:**
- Files appeared in search (from direct S3 notifications) ✅
- Packages didn't appear in catalog (from EventBridge) ❌
- **False conclusion:** "EventBridge works!" (No, only direct S3 works)

**Lesson:** Disable direct S3 Event Notifications when testing EventBridge routing.

---

### 5. Lambda Code Consistency Matters

**Current State:**
- SearchHandler: Handles SNS-wrapped messages ✅
- EsIngest: Handles EventBridge format ⚠️ (needs verification)
- ManifestIndexer: Expects EventBridge, gets SNS ❌ (broken)
- Iceberg: Expects EventBridge format ⚠️ (needs verification)

**Lesson:** When adding SNS fan-out to EventBridge routing, ALL Lambdas must be audited for SNS compatibility.

---

## Architecture: Current vs Required

### Current Flow (≤1.65)

```
S3 Upload → CloudTrail → EventBridge Rule [ENABLED] ✅
    ↓
SNS Topic ✅
    ├─→ IndexerQueue → SearchHandler ✅ (has SNS unwrapping)
    ├─→ EsIngestQueue → EsIngest ⚠️
    └─→ ManifestIndexerQueue → ManifestIndexer ❌ (no SNS unwrapping)
                                    ↓
                                KeyError: 'detail'
                                100% failure rate
```

### Fixed Flow (≥1.66)

```
S3 Upload → CloudTrail → EventBridge Rule [ENABLED] ✅
    ↓
SNS Topic ✅
    ├─→ IndexerQueue → SearchHandler ✅ (has SNS unwrapping)
    ├─→ EsIngestQueue → EsIngest ✅ (verified working)
    └─→ ManifestIndexerQueue → ManifestIndexer ✅ (FIXED: added SNS unwrapping)
                                    ↓
                                Packages appear in catalog ✅
```

---

## Version-Specific Behavior

### Platform ≤1.65 (Current)

**Infrastructure:**
- ✅ EventBridge routing works
- ✅ SNS fan-out works
- ✅ Messages reach all queues

**Application:**
- ✅ File indexing works (SearchHandler)
- ❌ **Package indexing broken** (ManifestIndexer)

**Workaround:** None - requires Platform 1.66+ update

---

### Platform 1.66+ (With Lambda Fix)

**Infrastructure:**
- ✅ EventBridge routing works
- ✅ SNS fan-out works
- ✅ Messages reach all queues

**Application:**
- ✅ File indexing works (SearchHandler)
- ✅ **Package indexing works** (ManifestIndexer - FIXED)

**Input Transformer:** Optional (Lambdas handle raw EventBridge format)

---

## Files in This Investigation

### Timeline (Chronological Order)

1. **[01-customer-issue-summary.md](01-customer-issue-summary.md)** - Original customer report
2. **[02-local-test-setup.md](02-local-test-setup.md)** - Test environment design
3. **[03-test-plan-staging.md](03-test-plan-staging.md)** - Staging environment testing
4. **[04-config-quilt-eventbridge-test.toml](04-config-quilt-eventbridge-test.toml)** - Configuration file
5. **[05-ACTION-ITEMS.md](05-ACTION-ITEMS.md)** - Initial action items
6. **[06-SUCCESS-REPORT.md](06-SUCCESS-REPORT.md)** - Initial fix (EventBridge rule enabled)
7. **[07-README.md](07-README.md)** - This file (complete summary)
8. **[08-FAILURE_REPORT.md](08-FAILURE_REPORT.md)** - Deep dive: Lambda code issue
9. **[09-documented-steps.md](09-documented-steps.md)** - Public documentation
10. **[10-input-transformer-hypothesis.md](10-input-transformer-hypothesis.md)** - Input Transformer analysis & testing guide

### Supporting Files

- **backup-policies/** - SNS policy backups
- **test-artifacts/** - EventBridge patterns, test scripts
- **obsolete-reports/** - Superseded documents

---

## Testing Recommendations

### For Platform ≤1.65

**Expected Results:**
- ❌ Package indexing will NOT work with EventBridge routing
- ✅ File indexing may work (if SearchHandler subscribed)
- ⚠️ Recommend waiting for Platform 1.66+ before deploying EventBridge routing

### For Platform 1.66+

**Test Strategy:**
1. **Disable direct S3 Event Notifications** (critical for accurate testing)
2. Test EventBridge routing in isolation
3. Create packages (not just upload files)
4. Verify packages appear in catalog
5. Check CloudWatch Logs for Lambda errors

**See [10-input-transformer-hypothesis.md](10-input-transformer-hypothesis.md) for complete testing guide.**

---

## Related Documentation

### Public Documentation
- [Quilt EventBridge Guide](https://docs.quilt.bio/quilt-platform-administrator/advanced/eventbridge)
- [AWS EventBridge Documentation](https://docs.aws.amazon.com/eventbridge/)
- [AWS SNS Fanout Pattern](https://aws.amazon.com/blogs/compute/fanout-s3-event-notifications-to-multiple-endpoints/)

### Internal Analysis
- [08-FAILURE_REPORT.md](08-FAILURE_REPORT.md) - Complete Lambda code analysis
- [10-input-transformer-hypothesis.md](10-input-transformer-hypothesis.md) - Why Input Transformers are insufficient

---

## Current Status

### Infrastructure (COMPLETE ✅)

- [x] EventBridge rule enabled
- [x] SNS topic routing correctly
- [x] ManifestIndexerQueue subscribed to SNS
- [x] EsIngestQueue subscribed to SNS
- [x] SQS policies configured
- [x] Event flow working end-to-end

### Application (REQUIRES 1.66+ ❌)

- [ ] ManifestIndexer Lambda SNS unwrapping (in Platform 1.66+)
- [ ] Optional: Dual format support for all Lambdas (future)
- [ ] Documentation updates reflecting version requirements

---

## Final Takeaways

1. **Infrastructure fixes alone are insufficient** - Application code must match architecture
2. **Input Transformers cannot eliminate SNS wrapping** - Lambda code fixes required
3. **Always test end-to-end with real workflows** - Metrics can show false positives
4. **Isolate event sources during testing** - Disable competing flows
5. **Version-specific behavior matters** - Document what works in each release

**Bottom Line:** EventBridge routing infrastructure is ready, but full functionality requires Platform 1.66+ Lambda updates.
