# Local Test Setup for EventBridge Routing

## Goal
Test the EventBridge routing setup locally to verify the documentation and identify the correct configuration.

## Prerequisites
- AWS CLI configured with credentials
- Access to AWS account for testing
- Permissions to create: S3, SNS, SQS, EventBridge, CloudTrail

## Test Environment

### Resources to Create
1. S3 bucket for testing
2. CloudTrail with S3 data events enabled
3. SNS topic (simulating Quilt's notification topic)
4. SQS queues (simulating Quilt's indexer queues)
5. EventBridge rule with proper event pattern and input transformer

## Test Plan

### Phase 1: Basic Infrastructure
```bash
# Set variables
TEST_REGION="us-east-1"
TEST_BUCKET="quilt-eventbridge-test-$(date +%s)"
TEST_SNS_TOPIC="quilt-eventbridge-test-notifications"
TEST_SQS_QUEUE="quilt-eventbridge-test-queue"
CLOUDTRAIL_NAME="quilt-eventbridge-test-trail"
CLOUDTRAIL_BUCKET="quilt-eventbridge-test-trail-logs-$(date +%s)"

# Create test bucket
aws s3 mb s3://${TEST_BUCKET} --region ${TEST_REGION}

# Create CloudTrail logging bucket
aws s3 mb s3://${CLOUDTRAIL_BUCKET} --region ${TEST_REGION}

# Create SNS topic
aws sns create-topic --name ${TEST_SNS_TOPIC} --region ${TEST_REGION}

# Create SQS queue
aws sqs create-queue --queue-name ${TEST_SQS_QUEUE} --region ${TEST_REGION}
```

### Phase 2: CloudTrail Configuration
This is the part the docs don't explain well.

```bash
# Get account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create CloudTrail bucket policy
# TODO: Add bucket policy for CloudTrail

# Create CloudTrail with S3 data events
# TODO: Add CloudTrail creation commands
```

### Phase 3: EventBridge Rule
```bash
# Create event pattern file
cat > event-pattern.json <<'EOF'
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
      "bucketName": ["${TEST_BUCKET}"]
    }
  }
}
EOF

# Create EventBridge rule
aws events put-rule \
  --name quilt-eventbridge-test-rule \
  --event-pattern file://event-pattern.json \
  --state ENABLED \
  --region ${TEST_REGION}
```

### Phase 4: Input Transformer (CRITICAL)
This is what the customer is missing!

```bash
# Create input transformer configuration
# This transforms CloudTrail events to S3 notification format

# Input paths - extract fields from CloudTrail event
cat > input-paths.json <<'EOF'
{
  "awsRegion": "$.detail.awsRegion",
  "bucketName": "$.detail.requestParameters.bucketName",
  "eventName": "$.detail.eventName",
  "eventTime": "$.time",
  "key": "$.detail.requestParameters.key",
  "principalId": "$.detail.userIdentity.principalId"
}
EOF

# Input template - construct S3 notification format
# QUESTION: What's the correct syntax for variables?
# Is it <awsRegion> or "<awsRegion>"?
cat > input-template.txt <<'EOF'
{
  "Records": [
    {
      "eventVersion": "2.1",
      "eventSource": "aws:s3",
      "awsRegion": "<awsRegion>",
      "eventTime": "<eventTime>",
      "eventName": "<eventName>",
      "userIdentity": {
        "principalId": "<principalId>"
      },
      "s3": {
        "s3SchemaVersion": "1.0",
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
EOF

# Add target with input transformer
aws events put-targets \
  --rule quilt-eventbridge-test-rule \
  --targets "Id"="1","Arn"="arn:aws:sns:${TEST_REGION}:${ACCOUNT_ID}:${TEST_SNS_TOPIC}","InputTransformer"="{\"InputPathsMap\"=$(cat input-paths.json | jq -c .),\"InputTemplate\":\"$(cat input-template.txt | jq -Rs .)\"}" \
  --region ${TEST_REGION}
```

### Phase 5: SNS to SQS Subscription
```bash
# Subscribe SQS to SNS
SNS_ARN=$(aws sns list-topics --region ${TEST_REGION} --query "Topics[?contains(TopicArn, '${TEST_SNS_TOPIC}')].TopicArn" --output text)
SQS_ARN=$(aws sqs get-queue-attributes --queue-url https://sqs.${TEST_REGION}.amazonaws.com/${ACCOUNT_ID}/${TEST_SQS_QUEUE} --attribute-names QueueArn --query "Attributes.QueueArn" --output text)

aws sns subscribe \
  --topic-arn ${SNS_ARN} \
  --protocol sqs \
  --notification-endpoint ${SQS_ARN} \
  --region ${TEST_REGION}

# Set SQS policy to allow SNS to send messages
# TODO: Add SQS policy
```

### Phase 6: Testing
```bash
# Upload a test file
echo "test content" > test-file.txt
aws s3 cp test-file.txt s3://${TEST_BUCKET}/test-file.txt

# Wait for event to flow through
sleep 10

# Check SQS for messages
aws sqs receive-message \
  --queue-url https://sqs.${TEST_REGION}.amazonaws.com/${ACCOUNT_ID}/${TEST_SQS_QUEUE} \
  --region ${TEST_REGION}
```

## Expected Results
1. CloudTrail captures S3 PutObject event
2. EventBridge rule matches the event
3. Input transformer converts to S3 notification format
4. SNS receives transformed event
5. SQS receives message from SNS
6. Message format matches S3 notification schema

## Key Things to Verify
1. Input transformer variable syntax (quoted vs unquoted)
2. Complete S3 event format (all required fields)
3. Event name mapping (CloudTrail vs S3 format)
4. IAM permissions at each step
5. Timing/latency

## Cleanup
```bash
# Delete all test resources
aws s3 rb s3://${TEST_BUCKET} --force
aws s3 rb s3://${CLOUDTRAIL_BUCKET} --force
aws sqs delete-queue --queue-url https://sqs.${TEST_REGION}.amazonaws.com/${ACCOUNT_ID}/${TEST_SQS_QUEUE}
aws sns delete-topic --topic-arn ${SNS_ARN}
aws events remove-targets --rule quilt-eventbridge-test-rule --ids 1
aws events delete-rule --name quilt-eventbridge-test-rule
aws cloudtrail delete-trail --name ${CLOUDTRAIL_NAME}
```

## Questions to Answer
1. What's the correct Input Transformer variable syntax?
2. What S3 event fields are actually required by Quilt?
3. Do we need event name mapping (PutObject → ObjectCreated:Put)?
4. What IAM permissions are needed at each step?
5. Does PackagerQueue need separate configuration?
