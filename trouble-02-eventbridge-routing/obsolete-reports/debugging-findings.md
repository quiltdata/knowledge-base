# Debugging Findings - EventBridge Pipeline

## The Actual Root Cause (Confirmed)

### Pipeline Flow
1. **EventBridge** → 2. **SNS Topic** → 3. **SQS Queue (indexer-queue)** → 4. **Lambda (search-handler)**

### What Was Broken

#### ✅ EventBridge Rule (Working)
- CloudWatch metrics confirmed EventBridge successfully receiving and processing events
- Event pattern was correct
- Rule was firing

#### ❌ SNS Topic Policy (BROKEN - This was the issue!)
**Problem**: SNS topic's access policy only allowed **S3** to publish, not **EventBridge**

**Original Policy** (incorrect):
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "s3.amazonaws.com"},
    "Action": "sns:Publish",
    "Resource": "arn:aws:sns:region:account:topic-name"
  }]
}
```

**Fixed Policy** (correct):
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "events.amazonaws.com"},
    "Action": "sns:Publish",
    "Resource": "arn:aws:sns:region:account:topic-name"
  }]
}
```

#### ❌ SQS Queue (No messages - consequence of SNS issue)
- Queue was correctly subscribed to SNS
- But received no messages because SNS was rejecting EventBridge publishes

#### ❌ Lambda (Not invoked - consequence of empty SQS)
- Lambda was configured correctly
- But never triggered because SQS queue was empty

## Key Insight

**Events were dying at the SNS boundary!**

EventBridge was firing → trying to publish to SNS → **SNS rejecting because policy only allowed s3.amazonaws.com** → messages never reached SQS → Lambda never triggered → packages never indexed.

## Documentation Gap

The current documentation shows:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "events.amazonaws.com"},
    "Action": "sns:Publish",
    "Resource": "arn:aws:sns:region:account:quilt-eventbridge-notifications"
  }]
}
```

**But it doesn't explain:**
1. **Where to apply this policy** (it's an SNS topic policy, not IAM)
2. **How to check existing policy** (SNS might already have S3-only policy)
3. **How to update/replace the policy** (not just set it)
4. **Common mistake**: If SNS was created for S3 notifications, it will have s3.amazonaws.com - this needs to be **changed** to events.amazonaws.com OR **both services added**

## What Actually Happened to Customer

1. Customer had existing SNS topic created by Quilt for S3 notifications
2. SNS topic policy allowed `s3.amazonaws.com` to publish
3. Customer created EventBridge rule targeting the same SNS topic
4. EventBridge tried to publish → SNS rejected (permission denied)
5. No error visible to customer in EventBridge console
6. SQS never received messages
7. Packages never indexed

## The Fix

**Option 1: Update existing SNS policy to allow EventBridge** (what was done)
```bash
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:region:account:topic-name \
  --attribute-name Policy \
  --attribute-value '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "events.amazonaws.com"},
      "Action": "sns:Publish",
      "Resource": "arn:aws:sns:region:account:topic-name"
    }]
  }'
```

**Option 2: Allow both S3 and EventBridge** (better for mixed environments)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "s3.amazonaws.com"},
      "Action": "sns:Publish",
      "Resource": "arn:aws:sns:region:account:topic-name",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "account-id"
        }
      }
    },
    {
      "Effect": "Allow",
      "Principal": {"Service": "events.amazonaws.com"},
      "Action": "sns:Publish",
      "Resource": "arn:aws:sns:region:account:topic-name"
    }
  ]
}
```

## Documentation Corrections Needed

### 1. Add Diagnostic Steps
**Before creating EventBridge rule**, verify SNS topic policy:
```bash
aws sns get-topic-attributes \
  --topic-arn arn:aws:sns:region:account:topic-name \
  --query 'Attributes.Policy' \
  --output text | jq .
```

### 2. Explain Policy Update (not just creation)
Show how to **update** existing SNS policy, not just set a new one.

### 3. Add Verification Steps
After setup, verify EventBridge can publish:
```bash
# Check EventBridge rule metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Events \
  --metric-name TriggeredRules \
  --dimensions Name=RuleName,Value=rule-name \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

# Check SNS topic for rejected publishes (this would show the error)
aws cloudwatch get-metric-statistics \
  --namespace AWS/SNS \
  --metric-name NumberOfNotificationsFailed \
  --dimensions Name=TopicName,Value=topic-name \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

### 4. Add Troubleshooting Section
**If events aren't flowing:**
- Check EventBridge metrics (is rule firing?)
- Check SNS topic policy (does it allow events.amazonaws.com?)
- Check SNS failed delivery metrics
- Check SQS queue (are messages arriving?)

## Questions Answered

1. ✅ **Input Transformer**: May still be needed for event format compatibility
2. ✅ **SNS Policy**: **THIS WAS THE ACTUAL BUG** - policy didn't allow EventBridge
3. ❓ **PackagerQueue**: Still unclear if this needs separate configuration
4. ✅ **Error visibility**: EventBridge doesn't show SNS permission errors clearly

## Next Steps

1. Update documentation to emphasize SNS policy check/update
2. Test whether Input Transformer is actually needed (or if raw CloudTrail format works)
3. Verify PackagerQueue subscription requirements
4. Add comprehensive troubleshooting guide
