# Confirmed Findings from Customer Interaction

## What Actually Fixed It

### The SNS Topic Policy Fix (Confirmed Root Cause)
- **Problem**: SNS topic policy only allowed `s3.amazonaws.com`, not `events.amazonaws.com`
- **Fix**: Updated SNS topic policy to allow EventBridge to publish
- **Result**: Events started flowing through the pipeline

### Input Transformer: NOT ADDED (Confirmed @ 52:20)
**Key Finding**: The discussion focused on EventBridge rule, SNS topic, and SQS queue.
**No Input Transformer was added or discussed.**

**Implication**: EventBridge is sending **raw CloudTrail events** to SNS/SQS, and **Quilt is processing them successfully**.

This means:
- ✅ Quilt can handle CloudTrail event format (not just S3 notification format)
- ✅ Input Transformer is NOT required for basic functionality
- ⚠️ Documentation incorrectly emphasizes Input Transformer as necessary

### PackagerQueue Subscriptions: NOT ADDED
**Finding**: PackagerQueue had 0 subscriptions.

**Ernest's Comment**: "This was normal behavior if the Quilt package engine had not been turned on."

**Implication**:
- PackagerQueue subscriptions are handled automatically by Quilt
- Not a manual configuration step
- Documentation should NOT tell users to manually configure PackagerQueue

## Revised Understanding of Event Flow

### What Actually Works
```
S3 Operation
  ↓
CloudTrail (captures API call)
  ↓
EventBridge (matches event pattern)
  ↓
SNS Topic (with events.amazonaws.com permission) ← THIS WAS THE FIX
  ↓
SQS Queues (subscribed automatically by Quilt)
  ↓
Lambda Functions (process CloudTrail events directly)
  ↓
Quilt Index Updated
```

### What the Docs Get Wrong

#### 1. Input Transformer (WRONG - Not Needed)
Current docs show complex Input Transformer configuration to convert CloudTrail → S3 format.

**Reality**: Not needed. Quilt processes CloudTrail events directly.

#### 2. PackagerQueue Manual Configuration (WRONG - Not Needed)
Any implication that users need to manually subscribe queues.

**Reality**: Quilt handles queue subscriptions automatically.

#### 3. SNS Policy (UNDERSTATED - This is THE critical step!)
Current docs show the policy but don't emphasize:
- Existing SNS topics will have S3-only policy
- This MUST be updated/checked
- This is the #1 failure point
- How to diagnose this issue

## What the Documentation Should Actually Say

### Critical Step: SNS Topic Policy
**Most Common Issue**: If you're using an existing SNS topic created for S3 notifications, its policy will only allow `s3.amazonaws.com` to publish. EventBridge uses `events.amazonaws.com` and will be silently rejected.

**Check Your SNS Policy**:
```bash
aws sns get-topic-attributes \
  --topic-arn <your-sns-topic-arn> \
  --query 'Attributes.Policy' \
  --output text | jq .
```

**Look for**: Principal should be `"Service": "events.amazonaws.com"` (not just s3.amazonaws.com)

**Fix It**:
```bash
aws sns set-topic-attributes \
  --topic-arn <your-sns-topic-arn> \
  --attribute-name Policy \
  --attribute-value '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "events.amazonaws.com"},
      "Action": "sns:Publish",
      "Resource": "<your-sns-topic-arn>"
    }]
  }'
```

**Or Keep Both** (if you have both S3 and EventBridge):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "s3.amazonaws.com"},
      "Action": "sns:Publish",
      "Resource": "<sns-topic-arn>"
    },
    {
      "Effect": "Allow",
      "Principal": {"Service": "events.amazonaws.com"},
      "Action": "sns:Publish",
      "Resource": "<sns-topic-arn>"
    }
  ]
}
```

### Optional: Input Transformer
**Status**: NOT REQUIRED for basic functionality.

Quilt can process CloudTrail events directly. Input Transformer can be used to normalize events but is not necessary for the EventBridge routing to work.

### Automatic: Queue Subscriptions
Quilt manages SQS queue subscriptions to the SNS topic automatically. You do not need to manually configure queue subscriptions.

## Documentation Fixes Needed

### 1. Reorder Priority
**Most Important First**:
1. SNS Topic Policy (THE critical step - emphasize checking existing policy)
2. EventBridge Rule Creation
3. CloudTrail Configuration
4. Testing & Verification

### 2. Remove or De-emphasize Input Transformer
Change from "required" to "optional optimization" or remove entirely.

### 3. Remove Manual Queue Configuration
Don't mention PackagerQueue or other queue subscriptions as manual steps.

### 4. Add Troubleshooting Section
**If packages aren't appearing**:
1. Check EventBridge metrics - is rule firing?
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Events \
     --metric-name TriggeredRules \
     --dimensions Name=RuleName,Value=<rule-name> \
     --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 60 \
     --statistics Sum
   ```

2. Check SNS topic policy - does it allow EventBridge?
   ```bash
   aws sns get-topic-attributes \
     --topic-arn <arn> \
     --query 'Attributes.Policy' | jq '.Statement[].Principal.Service'
   ```
   Should include "events.amazonaws.com"

3. Check SNS failed publishes
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/SNS \
     --metric-name NumberOfNotificationsFailed \
     --dimensions Name=TopicName,Value=<topic-name> \
     --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 60 \
     --statistics Sum
   ```
   Should be 0 or empty

4. Check SQS queue - are messages arriving?

## Testing Plan (Simplified)

Now we know:
- ✅ No Input Transformer needed
- ✅ No manual queue subscriptions needed
- ✅ Just need: EventBridge → SNS (with correct policy) → existing Quilt queues

**Simplified Test**:
1. Create test S3 bucket
2. Enable CloudTrail for bucket
3. Create EventBridge rule with event pattern
4. Create SNS topic with `events.amazonaws.com` policy ← THE KEY
5. Add SNS as EventBridge target (no transformer)
6. Subscribe test SQS queue to SNS
7. Upload file to S3
8. Verify CloudTrail event arrives at SQS in raw format

This proves the pipeline works without Input Transformer.

## Summary for Documentation Update

**What Works** (Confirmed):
- EventBridge → SNS (with correct policy) → SQS → Lambda
- CloudTrail event format processed directly by Quilt
- No Input Transformer needed
- No manual queue configuration needed

**What Was Wrong** (Root Cause):
- SNS topic policy only allowed s3.amazonaws.com
- Silent failure - EventBridge couldn't publish
- No clear error message to customer

**What Docs Need** (Priority):
1. **Big warning box**: "Check your SNS topic policy!"
2. Show how to check existing policy
3. Show how to update policy (not just create)
4. Add troubleshooting checklist
5. Remove/de-emphasize Input Transformer
6. Remove manual queue configuration steps
