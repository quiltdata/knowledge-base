# Questions for Customer (FL109)

## Current Status Verification

### 1. Is it working now after the SNS policy fix?
After updating the SNS topic policy to allow `events.amazonaws.com`, are packages now appearing in the UI when created?

### 2. Input Transformer Configuration
Looking at your screenshot, the EventBridge target shows "Input to target: Matched event" (not transformed).

**Question**: Did you add an Input Transformer, or is it still sending raw CloudTrail events?

**Why this matters**:
- CloudTrail format vs S3 notification format are different
- If it's working WITHOUT a transformer, that's important to document
- If you DID add a transformer, we need to see the configuration

### 3. PackagerQueue Subscription
Your screenshot showed `QuiltStack-PackagerQueue` had **0 SNS subscriptions**.

**Questions**:
- Did you need to manually subscribe PackagerQueue to the SNS topic?
- Or did Quilt automatically handle this?
- Are packages now being indexed properly?

### 4. Complete Event Flow Working?
Can you confirm all of these are working now:
- [ ] New files uploaded to S3 appear in file browser
- [ ] New packages created via UI appear in package list
- [ ] New packages created via quilt3 SDK appear in package list
- [ ] Package updates/revisions appear correctly

### 5. What Steps Actually Fixed It?
In order of what you did:
1. Created EventBridge rule with event pattern ✓
2. Set SNS topic as target ✓
3. Updated SNS topic policy to allow events.amazonaws.com ✓
4. Anything else?

**Specifically**:
- Did you add an Input Transformer to the EventBridge target?
- Did you manually subscribe any additional SQS queues to SNS?
- Did you re-index the bucket again after the SNS policy fix?

### 6. Testing & Verification
How did you verify it was working? What did you test?
- Upload a file → see it indexed?
- Create a package → see it in UI?
- How long did events take to appear (latency)?

### 7. Any Remaining Issues?
- Are all event types working (create, update, delete)?
- Any error messages in CloudWatch logs?
- Any performance/latency concerns?

## Documentation Clarity Questions

### 8. What Was Confusing in the Docs?
What parts of https://docs.quilt.bio/quilt-platform-administrator/advanced/eventbridge were unclear or incorrect?

Specific areas to comment on:
- CloudTrail setup instructions (clear enough?)
- EventBridge rule creation (easy to follow?)
- **SNS policy configuration (this seems to be the key gap!)**
- Input Transformer setup (was this mentioned? needed?)
- Testing/verification steps (helpful?)
- Troubleshooting guidance (would have helped?)

### 9. What Would Have Helped?
If you were writing this doc for the next person, what would you add?
- More detailed SNS policy update steps?
- How to check if SNS policy is wrong?
- Troubleshooting checklist?
- Complete CLI commands?
- Screenshots of each step?

### 10. SNS Policy - The Critical Detail
The SNS policy issue seems to be the root cause.

**Questions**:
- Did the docs mention checking/updating the SNS topic policy?
- When you first set the EventBridge target, did you get any error messages?
- How did you discover the SNS policy was wrong?
- What command/process did you use to update the SNS policy?

## Technical Details for Documentation

### 11. Your Working Configuration
Can you export your working configuration so we can document it?

```bash
# EventBridge rule
aws events describe-rule --name quilt-s3-events-rule-analytics

# EventBridge targets (this will show if Input Transformer is configured)
aws events list-targets-by-rule --rule quilt-s3-events-rule-analytics

# SNS topic policy (the critical fix)
aws sns get-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:622879846195:prod-fsp-data-platform-core-analytics-QuiltNotifications-a28a3959-7932-43fd-bfce-1114382382a6 \
  --query 'Attributes.Policy' \
  --output text | jq .

# SNS subscriptions
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-1:622879846195:prod-fsp-data-platform-core-analytics-QuiltNotifications-a28a3959-7932-43fd-bfce-1114382382a6
```

### 12. Sample Event
Can you capture a sample message from your SQS queue to see the actual event format that's working?

```bash
# Receive a message from one of your working queues
aws sqs receive-message \
  --queue-url <your-queue-url> \
  --max-number-of-messages 1
```

This will show us:
- Whether events are in CloudTrail or S3 notification format
- What fields Quilt actually needs
- Whether Input Transformer was required

## Summary

**Most Critical Questions** (in priority order):
1. **Is it working now?** (after SNS policy fix)
2. **Did you add Input Transformer?** (or working without it?)
3. **What fixed it?** (just SNS policy, or other changes?)
4. **How did you discover the SNS policy issue?** (for troubleshooting docs)
5. **Can you share working config?** (commands above)

**Documentation Questions**:
6. What was confusing/missing in current docs?
7. Did docs mention SNS policy at all?
8. What would have helped you debug faster?
