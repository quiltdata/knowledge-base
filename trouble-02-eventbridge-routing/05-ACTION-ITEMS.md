# Action Items - EventBridge Routing Fix

## Critical Issue Identified

**CloudTrail is NOT configured to send events to EventBridge**

This is why S3 events are not reaching the Quilt indexing pipeline via EventBridge.

## Immediate Actions Required

### 1. Enable EventBridge in CloudTrail (PRIORITY 1)

**Via AWS Console:**
1. Go to [CloudTrail Console](https://console.aws.amazon.com/cloudtrail/home?region=us-east-1)
2. Click on "analytics" trail
3. Click "Edit"
4. Scroll to "Event delivery" section
5. Check "Amazon EventBridge"
6. Click "Save changes"

**Verification Command:**
```bash
aws cloudtrail get-trail --name analytics --profile default --region us-east-1 --output json | jq '.Trail.EventBridgeEnabled'
# Should return: true
```

### 2. Re-run Test After Enabling (PRIORITY 2)

After enabling EventBridge in CloudTrail:

```bash
# Wait 5 minutes for changes to propagate
sleep 300

# Upload a new test file
echo "Test after enabling EventBridge - $(date)" > /tmp/test-file.txt
aws s3 cp /tmp/test-file.txt s3://quilt-eventbridge-test/test/eventbridge-enabled-test.txt

# Wait 2 minutes for CloudTrail
sleep 120

# Check EventBridge metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Events \
  --metric-name Invocations \
  --dimensions Name=RuleName,Value=quilt-staging-eventbridge-test-v2 \
  --start-time $(date -u -v-5M +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --profile default

# Check SQS queue
aws sqs get-queue-attributes \
  --queue-url "https://sqs.us-east-1.amazonaws.com/712023778557/quilt-staging-IndexerQueue-yD8FCAN9MJWr" \
  --attribute-names ApproximateNumberOfMessages \
  --profile default
```

### 3. Update Infrastructure as Code (PRIORITY 3)

Add EventBridge configuration to CloudFormation/Terraform:

**CloudFormation:**
```yaml
Trail:
  Type: AWS::CloudTrail::Trail
  Properties:
    TrailName: analytics
    EventBridgeEnabled: true  # Add this line
    # ... other properties
```

**Terraform:**
```hcl
resource "aws_cloudtrail" "analytics" {
  name = "analytics"
  enable_event_bridge = true  # Add this line
  # ... other configuration
}
```

### 4. Clean Up Test Resources (After Testing)

```bash
# Run the cleanup script
./cleanup-test-resources.sh
```

## Long-term Recommendations

1. **Documentation Update**
   - Add CloudTrail EventBridge requirement to setup docs
   - Include in troubleshooting guide

2. **Monitoring Setup**
   - Add CloudWatch alarm for EventBridge rule invocations
   - Monitor SNS/SQS message flow

3. **Testing Strategy**
   - Include EventBridge configuration check in deployment validation
   - Add integration tests for the full pipeline

## Files Created During Testing

- `/Users/ernest/GitHub/knowledge-base/trouble-02-eventbridge-routing/TEST-REPORT-V2.md` - Comprehensive test report
- `/Users/ernest/GitHub/knowledge-base/trouble-02-eventbridge-routing/config-quilt-eventbridge-test.toml` - Test configuration with results
- `/Users/ernest/GitHub/knowledge-base/trouble-02-eventbridge-routing/cleanup-test-resources.sh` - Cleanup script
- `/Users/ernest/GitHub/knowledge-base/trouble-02-eventbridge-routing/enable-eventbridge.py` - Python script (shows API limitation)

## Success Criteria

After enabling EventBridge in CloudTrail, the following should occur:
1. ✅ EventBridge rule receives S3 events from CloudTrail
2. ✅ EventBridge publishes to SNS topic
3. ✅ SNS delivers to SQS queues
4. ✅ Lambda functions process messages
5. ✅ Files get indexed in Quilt

## Support Contact

If issues persist after enabling EventBridge:
- Check CloudWatch Logs for errors
- Verify IAM permissions
- Ensure all resources are in us-east-1 region