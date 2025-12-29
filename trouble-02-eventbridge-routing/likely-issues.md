# Likely Issues Analysis

Based on reviewing the documentation, here are the most probable issues customers are encountering:

## Critical Issue #1: Input Transformer Syntax ⚠️

**Problem**: The Input Template uses ambiguous variable syntax.

**Documented Template:**
```json
{
  "Records": [
    {
      "awsRegion": <awsRegion>,
      "eventName": <eventName>,
      "eventTime": <eventTime>,
      "s3": {
        "bucket": {
          "name": <bucketName>
        },
        "object": {
          "key": <key>
        }
      }
    }
  ]
}
```

**Issue**: Variables like `<awsRegion>` should likely be quoted as strings: `"<awsRegion>"`

**Why This Breaks**: AWS EventBridge input transformer requires proper quoting. Unquoted variables will cause:
- JSON validation errors
- Rule creation failure
- Invalid event transformation

**Correct Syntax Should Be:**
```json
{
  "Records": [
    {
      "awsRegion": "<awsRegion>",
      "eventName": "<eventName>",
      "eventTime": "<eventTime>",
      "s3": {
        "bucket": {
          "name": "<bucketName>"
        },
        "object": {
          "key": "<key>"
        }
      }
    }
  ]
}
```

## Critical Issue #2: Incomplete S3 Event Format

**Problem**: The transformed event is missing critical S3 event notification fields.

**Current Output**: Only includes awsRegion, eventName, eventTime, bucket name, and object key.

**S3 Event Format Requires**:
```json
{
  "Records": [
    {
      "eventVersion": "2.1",
      "eventSource": "aws:s3",
      "awsRegion": "us-east-1",
      "eventTime": "2024-01-01T00:00:00.000Z",
      "eventName": "ObjectCreated:Put",
      "userIdentity": { ... },
      "requestParameters": { ... },
      "responseElements": { ... },
      "s3": {
        "s3SchemaVersion": "1.0",
        "configurationId": "...",
        "bucket": {
          "name": "bucket-name",
          "ownerIdentity": { ... },
          "arn": "arn:aws:s3:::bucket-name"
        },
        "object": {
          "key": "object-key",
          "size": 1234,
          "eTag": "...",
          "sequencer": "..."
        }
      }
    }
  ]
}
```

**Missing Fields**:
- `eventVersion`
- `eventSource` (should be "aws:s3")
- `s3SchemaVersion`
- `bucket.arn`
- `object.size`
- `object.eTag`

**Impact**: Quilt may fail to process events due to missing required fields.

## Critical Issue #3: Event Name Mapping

**Problem**: CloudTrail event names don't match S3 notification event names.

**CloudTrail Events**:
- `PutObject`
- `CopyObject`
- `CompleteMultipartUpload`
- `DeleteObject`

**S3 Notification Events**:
- `ObjectCreated:Put`
- `ObjectCreated:Copy`
- `ObjectCreated:CompleteMultipartUpload`
- `ObjectRemoved:Delete`

**Impact**: Quilt expects S3 notification format event names, not CloudTrail API event names.

**Solution Needed**: Input transformer must map event names:
```
PutObject -> ObjectCreated:Put
CopyObject -> ObjectCreated:Copy
CompleteMultipartUpload -> ObjectCreated:CompleteMultipartUpload
DeleteObject -> ObjectRemoved:Delete
DeleteObjects -> ObjectRemoved:DeleteMarkerCreated
```

## Major Issue #4: IAM Policy Unclear

**Problem**: Documentation shows IAM policy but doesn't explain where to apply it.

**Question**: Is this:
- An SNS Topic Policy (resource-based)?
- An IAM Role Policy for EventBridge?
- Both?

**Missing**:
- CLI command to apply the policy
- Console steps to apply the policy
- How to get the actual ARN values

**Correct Approach Should Be**:
```bash
# Apply as SNS Topic Policy
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:region:account:quilt-eventbridge-notifications \
  --attribute-name Policy \
  --attribute-value '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "events.amazonaws.com"},
      "Action": "sns:Publish",
      "Resource": "arn:aws:sns:region:account:quilt-eventbridge-notifications"
    }]
  }'
```

## Major Issue #5: CloudTrail Setup Not Documented

**Problem**: "Verify CloudTrail configuration" assumes CloudTrail exists.

**Customer Challenge**:
- How do I know if CloudTrail is enabled?
- How do I enable S3 data events in CloudTrail?
- What if I don't have CloudTrail set up?

**Missing Steps**:
1. Check existing CloudTrail:
```bash
aws cloudtrail list-trails
aws cloudtrail get-event-selectors --trail-name <name>
```

2. Create CloudTrail with S3 data events:
```bash
aws cloudtrail create-trail --name quilt-s3-events --s3-bucket-name <logging-bucket>
aws cloudtrail put-event-selectors --trail-name quilt-s3-events --event-selectors '[{
  "ReadWriteType": "WriteOnly",
  "IncludeManagementEvents": false,
  "DataResources": [{
    "Type": "AWS::S3::Object",
    "Values": ["arn:aws:s3:::<your-bucket>/*"]
  }]
}]'
aws cloudtrail start-logging --name quilt-s3-events
```

## Major Issue #6: EventBridge Rule Target Not Documented

**Problem**: Documentation says "create rule" but doesn't specify setting the target.

**Missing Step**: After creating the rule and setting the event pattern, you must:
1. Add SNS topic as a target
2. Configure the input transformer on the target
3. Enable the rule

**Console Steps Missing**:
- Where to click "Add target"
- How to select SNS
- Where to configure input transformer (it's on the target, not the rule)

**CLI Command Missing**:
```bash
aws events put-targets \
  --rule quilt-s3-events-rule \
  --targets '{
    "Id": "1",
    "Arn": "arn:aws:sns:region:account:quilt-eventbridge-notifications",
    "InputTransformer": {
      "InputPathsMap": { ... },
      "InputTemplate": "..."
    }
  }'
```

## Minor Issue #7: Testing Guidance Inadequate

**Problem**: "Upload test file and verify" doesn't help debug failures.

**Better Testing Approach**:
1. Use EventBridge test event feature
2. Check CloudTrail event structure first
3. Verify EventBridge rule metrics
4. Check SNS delivery logs
5. Test transformation with sample event
6. Check Quilt logs for processing errors

## Minor Issue #8: Quilt Configuration Steps Vague

**Problem**: "Add bucket in Quilt Admin Panel" lacks detail.

**Questions**:
- Where is the SNS ARN field?
- What does "disable direct S3 notifications" mean?
- Is this a checkbox? A separate config?
- Screenshot needed?

## Summary of Fixes Needed

1. **Fix Input Transformer syntax** with proper quoting
2. **Complete S3 event format** with all required fields
3. **Add event name mapping** (CloudTrail → S3 format)
4. **Document IAM policy application** with CLI commands
5. **Add CloudTrail setup instructions** from scratch
6. **Document EventBridge target configuration** clearly
7. **Improve testing/debugging guidance**
8. **Add screenshots** for Quilt Admin Panel steps
9. **Provide complete working example** end-to-end
10. **Add troubleshooting section** for common errors

## Next Steps

1. Set up test environment with real AWS resources
2. Execute each step and document actual commands/clicks needed
3. Capture exact error messages
4. Create corrected documentation with working example
5. Test corrected version end-to-end
