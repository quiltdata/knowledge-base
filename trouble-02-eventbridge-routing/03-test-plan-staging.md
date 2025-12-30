# EventBridge Routing Test Plan - Quilt Staging Environment

## Test Environment
- **AWS Profile**: default
- **Region**: us-east-1 (US East N. Virginia)
- **Quilt Stack**: quilt-staging
- **Test Bucket**: aneesh-test-service

## Objective
Verify that EventBridge → SNS → SQS pipeline works **without Input Transformer** by sending raw CloudTrail events to Quilt's existing infrastructure.

## Prerequisites Check

### 1. Verify AWS Access
```bash
# Check current profile and region
aws sts get-caller-identity
aws configure get region

# Expected: us-east-1
```

### 2. Verify Test Bucket Exists
```bash
aws s3 ls s3://aneesh-test-service/ --region us-east-1
```

### 3. Identify Quilt Staging Resources
```bash
# Find quilt-staging stack
aws cloudformation describe-stacks \
  --stack-name quilt-staging \
  --region us-east-1 \
  --query 'Stacks[0].StackStatus'

# Get stack outputs (SNS topic, SQS queues, etc.)
aws cloudformation describe-stacks \
  --stack-name quilt-staging \
  --region us-east-1 \
  --query 'Stacks[0].Outputs' \
  --output table
```

### 4. Find Quilt SNS Topic
```bash
# List SNS topics to find quilt-staging notification topic
aws sns list-topics --region us-east-1 | grep -i quilt-staging

# Or get from CloudFormation outputs
aws cloudformation describe-stacks \
  --stack-name quilt-staging \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`SNSTopicArn`].OutputValue' \
  --output text
```

### 5. Check CloudTrail Status
```bash
# List CloudTrail trails
aws cloudtrail list-trails --region us-east-1

# Check if S3 data events are enabled for our bucket
aws cloudtrail get-event-selectors \
  --trail-name <trail-name> \
  --region us-east-1
```

## Test Procedure

### Step 1: Check Current SNS Topic Policy

**Purpose**: Verify what the current policy allows before we add EventBridge.

```bash
# Set variables
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
SNS_TOPIC_ARN="<from-step-4-above>"

# Get current SNS topic policy
aws sns get-topic-attributes \
  --topic-arn ${SNS_TOPIC_ARN} \
  --query 'Attributes.Policy' \
  --output text | jq . > current-sns-policy.json

# Check what services are currently allowed
cat current-sns-policy.json | jq '.Statement[].Principal.Service'
```

**Expected**: Likely shows `s3.amazonaws.com` but NOT `events.amazonaws.com`

**Save this**: We'll need to restore it if something goes wrong.

### Step 2: Create EventBridge Rule

```bash
# Create event pattern file
cat > eventbridge-pattern.json <<EOF
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
      "bucketName": ["aneesh-test-service"]
    }
  }
}
EOF

# Create EventBridge rule
aws events put-rule \
  --name quilt-staging-eventbridge-test \
  --event-pattern file://eventbridge-pattern.json \
  --state ENABLED \
  --description "Test EventBridge routing for aneesh-test-service bucket" \
  --region us-east-1

# Verify rule was created
aws events describe-rule \
  --name quilt-staging-eventbridge-test \
  --region us-east-1
```

### Step 3: Update SNS Topic Policy (THE CRITICAL FIX)

**Purpose**: Allow EventBridge to publish to the SNS topic.

```bash
# Get current policy
CURRENT_POLICY=$(aws sns get-topic-attributes \
  --topic-arn ${SNS_TOPIC_ARN} \
  --query 'Attributes.Policy' \
  --output text)

# Create new policy that allows BOTH s3.amazonaws.com AND events.amazonaws.com
cat > new-sns-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowS3ToPublish",
      "Effect": "Allow",
      "Principal": {
        "Service": "s3.amazonaws.com"
      },
      "Action": "sns:Publish",
      "Resource": "${SNS_TOPIC_ARN}",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "${ACCOUNT_ID}"
        }
      }
    },
    {
      "Sid": "AllowEventBridgeToPublish",
      "Effect": "Allow",
      "Principal": {
        "Service": "events.amazonaws.com"
      },
      "Action": "sns:Publish",
      "Resource": "${SNS_TOPIC_ARN}"
    }
  ]
}
EOF

# Apply the new policy
aws sns set-topic-attributes \
  --topic-arn ${SNS_TOPIC_ARN} \
  --attribute-name Policy \
  --attribute-value file://new-sns-policy.json \
  --region us-east-1

# Verify the policy was updated
aws sns get-topic-attributes \
  --topic-arn ${SNS_TOPIC_ARN} \
  --query 'Attributes.Policy' \
  --output text | jq '.Statement[].Principal.Service'
```

**Expected**: Should now show both `"s3.amazonaws.com"` and `"events.amazonaws.com"`

### Step 4: Add SNS as EventBridge Target (NO Input Transformer)

**Purpose**: Route EventBridge events to SNS **without transformation**.

```bash
# Add SNS topic as target
# NOTE: We're NOT adding an InputTransformer - sending raw CloudTrail events
aws events put-targets \
  --rule quilt-staging-eventbridge-test \
  --targets \
    "Id"="1",\
    "Arn"="${SNS_TOPIC_ARN}" \
  --region us-east-1

# Verify target was added
aws events list-targets-by-rule \
  --rule quilt-staging-eventbridge-test \
  --region us-east-1
```

**Verify**: Should show SNS ARN as target with NO InputTransformer section.

### Step 5: Verify SQS Queue Subscriptions

**Purpose**: Check that Quilt's SQS queues are subscribed to the SNS topic.

```bash
# List all subscriptions to the SNS topic
aws sns list-subscriptions-by-topic \
  --topic-arn ${SNS_TOPIC_ARN} \
  --region us-east-1 \
  --query 'Subscriptions[].{Protocol:Protocol,Endpoint:Endpoint}' \
  --output table
```

**Expected**: Should see SQS queue subscriptions (IndexerQueue, etc.)

**Note**: PackagerQueue may have 0 subscriptions (normal if package engine not enabled)

### Step 6: Baseline Monitoring - Before Test

**Purpose**: Capture current state before we trigger events.

```bash
# Check EventBridge rule metrics (should be 0 before test)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Events \
  --metric-name TriggeredRules \
  --dimensions Name=RuleName,Value=quilt-staging-eventbridge-test \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Sum \
  --region us-east-1

# Check SNS failed publishes (should be empty/0)
aws cloudwatch get-metric-statistics \
  --namespace AWS/SNS \
  --metric-name NumberOfNotificationsFailed \
  --dimensions Name=TopicName,Value=$(echo ${SNS_TOPIC_ARN} | awk -F: '{print $NF}') \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Sum \
  --region us-east-1
```

### Step 7: Trigger Test Event

**Purpose**: Upload a file to generate S3 event → CloudTrail → EventBridge → SNS → SQS.

```bash
# Create a test file
echo "EventBridge test - $(date)" > eventbridge-test-file.txt

# Upload to test bucket
aws s3 cp eventbridge-test-file.txt s3://aneesh-test-service/test/eventbridge-test-file.txt --region us-east-1

# Timestamp for reference
echo "Test file uploaded at: $(date -u +%Y-%m-%dT%H:%M:%S)"
```

### Step 8: Wait and Monitor

**Purpose**: CloudTrail events typically take 1-5 minutes to appear.

```bash
# Wait 2 minutes
echo "Waiting 2 minutes for CloudTrail to process event..."
sleep 120

# Check if EventBridge rule was triggered
aws cloudwatch get-metric-statistics \
  --namespace AWS/Events \
  --metric-name TriggeredRules \
  --dimensions Name=RuleName,Value=quilt-staging-eventbridge-test \
  --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Sum \
  --region us-east-1 \
  --query 'Datapoints[*].[Timestamp,Sum]' \
  --output table
```

**Expected**: Should show Sum > 0 (rule triggered)

### Step 9: Check SNS Delivery

```bash
# Check SNS successful publishes
aws cloudwatch get-metric-statistics \
  --namespace AWS/SNS \
  --metric-name NumberOfMessagesPublished \
  --dimensions Name=TopicName,Value=$(echo ${SNS_TOPIC_ARN} | awk -F: '{print $NF}') \
  --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Sum \
  --region us-east-1 \
  --query 'Datapoints[*].[Timestamp,Sum]' \
  --output table

# Check for failed publishes (should be 0 or empty)
aws cloudwatch get-metric-statistics \
  --namespace AWS/SNS \
  --metric-name NumberOfNotificationsFailed \
  --dimensions Name=TopicName,Value=$(echo ${SNS_TOPIC_ARN} | awk -F: '{print $NF}') \
  --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Sum \
  --region us-east-1
```

**Expected**: Messages published > 0, failed = 0

### Step 10: Check SQS Queue for Events

**Purpose**: Verify raw CloudTrail events arrived at SQS.

```bash
# Get IndexerQueue URL from CloudFormation
INDEXER_QUEUE_URL=$(aws cloudformation describe-stacks \
  --stack-name quilt-staging \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?contains(OutputKey,`IndexerQueue`)].OutputValue' \
  --output text)

# Receive message from queue (non-destructive)
aws sqs receive-message \
  --queue-url ${INDEXER_QUEUE_URL} \
  --max-number-of-messages 1 \
  --region us-east-1 \
  --query 'Messages[0].Body' \
  --output text | jq . > received-event.json

# Display the event
cat received-event.json
```

**Verify Event Format**:
```bash
# Check if it's a CloudTrail event (not S3 notification format)
cat received-event.json | jq '.detail.eventName'
# Should show: "PutObject" (CloudTrail format)
# NOT "ObjectCreated:Put" (S3 format)

# This confirms NO Input Transformer was needed!
```

### Step 11: Check Quilt Indexing (End-to-End Verification)

**Purpose**: Verify Quilt actually processed the event and indexed the file.

```bash
# Check SearchHandler Lambda invocations
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=quilt-staging-SearchHandler \
  --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Sum \
  --region us-east-1

# Check for Lambda errors
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=quilt-staging-SearchHandler \
  --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Sum \
  --region us-east-1
```

**Expected**: Invocations > 0, Errors = 0

**Manual Check**: Visit Quilt UI and verify `eventbridge-test-file.txt` appears in `aneesh-test-service` bucket.

## Success Criteria

✅ **Test passes if**:
1. EventBridge rule triggered (metrics > 0)
2. SNS published messages successfully (no failures)
3. SQS received CloudTrail format event (NOT S3 format)
4. Lambda processed event without errors
5. File appears in Quilt UI

✅ **Confirms**:
- No Input Transformer needed
- SNS policy fix is the key
- Quilt processes CloudTrail events natively

## Troubleshooting

### If EventBridge rule doesn't trigger:
```bash
# Verify CloudTrail is capturing S3 data events
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=aneesh-test-service \
  --max-results 5 \
  --region us-east-1

# Check EventBridge rule pattern
aws events describe-rule --name quilt-staging-eventbridge-test --region us-east-1
```

### If SNS shows failed publishes:
```bash
# This means SNS policy is still wrong
aws sns get-topic-attributes \
  --topic-arn ${SNS_TOPIC_ARN} \
  --query 'Attributes.Policy' | jq '.Statement[].Principal.Service'

# Should include "events.amazonaws.com"
```

### If SQS queue is empty:
```bash
# Check queue is subscribed to SNS
aws sns list-subscriptions-by-topic \
  --topic-arn ${SNS_TOPIC_ARN} \
  --region us-east-1

# Check SQS queue policy allows SNS to send
aws sqs get-queue-attributes \
  --queue-url ${INDEXER_QUEUE_URL} \
  --attribute-names Policy \
  --region us-east-1
```

## Cleanup

```bash
# Remove EventBridge target
aws events remove-targets \
  --rule quilt-staging-eventbridge-test \
  --ids 1 \
  --region us-east-1

# Delete EventBridge rule
aws events delete-rule \
  --name quilt-staging-eventbridge-test \
  --region us-east-1

# Restore original SNS policy (if needed)
aws sns set-topic-attributes \
  --topic-arn ${SNS_TOPIC_ARN} \
  --attribute-name Policy \
  --attribute-value file://current-sns-policy.json \
  --region us-east-1

# Delete test file
aws s3 rm s3://aneesh-test-service/test/eventbridge-test-file.txt

# Clean up local files
rm eventbridge-pattern.json new-sns-policy.json current-sns-policy.json eventbridge-test-file.txt received-event.json
```

## Test Results Log

Document findings here:

### Test Date/Time:
### Tester:
### Results:
- [ ] EventBridge rule triggered
- [ ] SNS published successfully
- [ ] SQS received CloudTrail event (raw format)
- [ ] Lambda processed event
- [ ] File indexed in Quilt UI

### Event Format Captured:
```json
(paste received-event.json here)
```

### Notes:
- Any errors encountered?
- CloudTrail delay observed?
- Any unexpected behavior?

### Conclusion:
- Does EventBridge → SNS → SQS work without Input Transformer? YES/NO
- Is SNS policy the critical configuration? YES/NO
- Ready to update documentation? YES/NO
