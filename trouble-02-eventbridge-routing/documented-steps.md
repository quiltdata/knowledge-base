# Current Documentation Steps (As Published)

Source: https://docs.quilt.bio/quilt-platform-administrator/advanced/eventbridge

## Prerequisites
- AWS CLI or Console access
- Existing Quilt deployment
- Target S3 bucket
- CloudTrail enabled for the bucket

## Step 1: Create SNS Topic
```bash
aws sns create-topic \
    --name quilt-eventbridge-notifications \
    --region us-east-1
```

## Step 2: Verify CloudTrail Configuration
- Confirm CloudTrail is tracking S3 data events
- Ensure your bucket is included in the trail

## Step 3: Create EventBridge Rule
- Navigate to EventBridge Console
- Create rule named `quilt-s3-events-rule`

## Step 4: Configure Event Pattern
Key events to capture:
- PutObject
- CopyObject
- CompleteMultipartUpload
- DeleteObject
- DeleteObjects

Event Pattern JSON:
```json
{
  "source": ["aws.s3"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventSource": ["s3.amazonaws.com"],
    "eventName": [
      "PutObject",
      "CopyObject",
      "CompleteMultipartUpload",
      "DeleteObject",
      "DeleteObjects"
    ],
    "requestParameters": {
      "bucketName": ["your-bucket-name"]
    }
  }
}
```

## Step 5: Configure Input Transformer
Transform EventBridge events to S3 event format:

**Input Path:**
```json
{
  "awsRegion": "$.detail.awsRegion",
  "bucketName": "$.detail.requestParameters.bucketName",
  "eventName": "$.detail.eventName",
  "eventTime": "$.detail.eventTime",
  "key": "$.detail.requestParameters.key"
}
```

**Input Template:**
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

## Step 6: Set Up IAM Permissions
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "events.amazonaws.com"
      },
      "Action": "sns:Publish",
      "Resource": "arn:aws:sns:region:account:quilt-eventbridge-notifications"
    }
  ]
}
```

## Step 7: Configure Quilt
- Add bucket in Quilt Admin Panel
- Use the SNS topic ARN
- Disable direct S3 Event Notifications

## Step 8: Perform Initial Indexing
- Re-index bucket without "Repair" option

## Testing
- Upload test file to S3 bucket
- Verify event appears in Quilt catalog
- Check SNS and EventBridge metrics
