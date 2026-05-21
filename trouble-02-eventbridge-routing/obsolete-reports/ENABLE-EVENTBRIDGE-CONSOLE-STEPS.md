# Enable EventBridge for CloudTrail - Console Steps

## The Problem

CloudTrail is logging S3 data events BUT is not forwarding them to EventBridge. This requires a trail-level setting that **cannot be enabled via AWS CLI**.

## Verified Facts

✅ CloudTrail "analytics" trail is active and logging
✅ S3 bucket "quilt-eventbridge-test" IS in CloudTrail event selectors
✅ EventBridge rule created successfully
✅ SNS permissions updated correctly
✅ SQS queues properly subscribed
❌ **CloudTrail NOT sending events to EventBridge**

## Test Results

- Uploaded test file to s3://quilt-eventbridge-test/test/test-file-v3.txt
- Waited 3 minutes for CloudTrail processing
- **Result: EventBridge rule was NOT triggered (0 invocations)**

## Solution: Enable via AWS Console

### Step-by-Step Instructions

1. **Open CloudTrail Console**
   - Navigate to: https://console.aws.amazon.com/cloudtrail/
   - Region: US East (N. Virginia) us-east-1

2. **Select the Trail**
   - Click on "Trails" in the left sidebar
   - Click on "analytics" trail

3. **Edit Trail Settings**
   - Click the "Edit" button (top right)

4. **Enable EventBridge Integration**
   - Scroll to the "Event delivery" section
   - Look for checkbox: **"Send events to Amazon EventBridge"** or **"Integration with Amazon EventBridge"**
   - ✅ **Check this box to enable**

5. **Save Changes**
   - Click "Save changes" button at the bottom
   - Wait for the trail to update (usually instant)

6. **Verify**
   - Return to trail details page
   - Confirm EventBridge integration shows as "Enabled"

### Alternative: Check Current Setting

To see if EventBridge is already enabled:
1. Go to CloudTrail Console → analytics trail
2. Look at "General details" section
3. Check "EventBridge integration" field

## After Enabling

Once EventBridge integration is enabled:

1. **Test immediately**:
   ```bash
   cd /Users/ernest/GitHub/knowledge-base/trouble-02-eventbridge-routing

   # Upload a test file
   echo "Test after EventBridge enabled - $(date)" > test-post-enable.txt
   aws s3 cp test-post-enable.txt s3://quilt-eventbridge-test/test/test-post-enable.txt --region us-east-1

   # Wait 2 minutes
   sleep 120

   # Check EventBridge metrics
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Events \
     --metric-name TriggeredRules \
     --dimensions Name=RuleName,Value=quilt-staging-eventbridge-test-v2 \
     --start-time $(date -u -v-5M '+%Y-%m-%dT%H:%M:%S') \
     --end-time $(date -u '+%Y-%m-%dT%H:%M:%S') \
     --period 60 \
     --statistics Sum \
     --region us-east-1
   ```

2. **Check SQS Queue**:
   ```bash
   # Check for messages
   aws sqs receive-message \
     --queue-url https://sqs.us-east-1.amazonaws.com/712023778557/quilt-staging-IndexerQueue-yD8FCAN9MJWr \
     --max-number-of-messages 1 \
     --region us-east-1
   ```

## Why CLI Doesn't Work

The AWS CLI `cloudtrail` commands do not expose the EventBridge integration setting:
- `aws cloudtrail create-trail` - No EventBridge parameter
- `aws cloudtrail update-trail` - No EventBridge parameter
- `aws cloudtrail get-trail` - Does not show EventBridge status

This is a known limitation. The setting must be managed via:
- AWS Console (manual)
- CloudFormation (infrastructure as code)
- Terraform (infrastructure as code)

## CloudFormation Alternative

If the trail was created via CloudFormation, add this property:

```yaml
Resources:
  AnalyticsTrail:
    Type: AWS::CloudTrail::Trail
    Properties:
      TrailName: analytics
      S3BucketName: quilt-staging-cloudtrail
      IsLogging: true
      EventSelectors:
        - ReadWriteType: All
          IncludeManagementEvents: false
          DataResources:
            - Type: AWS::S3::Object
              Values:
                - arn:aws:s3:::quilt-eventbridge-test/*
      # ADD THIS:
      InsightSelectors:
        - InsightType: ApiCallRateInsight
      # Note: EventBridge integration is automatic when EventSelectors are present
```

Actually, based on 2024 AWS docs, EventBridge integration should be automatic. The issue might be different. Let me check if there's a service-linked role issue.

## Status

🔴 **Awaiting manual console change to enable EventBridge integration**

Once enabled, the entire pipeline should work immediately:
- S3 upload → CloudTrail → **EventBridge** → SNS → SQS → Lambda

---

**Next Step:** Enable EventBridge in AWS Console, then re-run test
