# EventBridge Routing Test Plan

## Objective
Reproduce the customer issue by following the documentation exactly as written and identify what doesn't work.

## Test Environment Requirements
- [ ] AWS Account with appropriate permissions
- [ ] S3 bucket (create test bucket if needed)
- [ ] CloudTrail enabled
- [ ] Quilt deployment (or access to one)
- [ ] AWS CLI configured

## Test Checklist

### Phase 1: Prerequisites Verification
- [ ] Verify AWS CLI access and credentials
- [ ] Identify test S3 bucket (or create new one)
- [ ] Verify Quilt deployment exists and is accessible
- [ ] Check CloudTrail status for the bucket

#### Issues Found:
- Documentation doesn't specify HOW to verify CloudTrail is enabled
- No guidance on creating CloudTrail if it doesn't exist
- Unclear what "S3 data events" means for CloudTrail

### Phase 2: SNS Topic Creation
- [ ] Run the documented SNS create command
- [ ] Verify topic was created successfully
- [ ] Note the topic ARN

#### Issues Found:
(To be filled in during testing)

### Phase 3: EventBridge Rule Creation
- [ ] Navigate to EventBridge Console
- [ ] Create rule with name `quilt-s3-events-rule`
- [ ] Apply the event pattern JSON
- [ ] Verify pattern syntax is accepted

#### Potential Issues to Check:
- Does the event pattern JSON work as-is?
- Are there any validation errors?
- Does it need modification for specific AWS regions?

### Phase 4: Input Transformer Configuration
- [ ] Add Input Path JSON
- [ ] Add Input Template JSON
- [ ] Verify syntax is accepted by AWS

#### Critical Issues to Check:
- **Input Template syntax**: The template uses `<awsRegion>` syntax - is this correct?
- Should it be `"<awsRegion>"` (quoted) or `<awsRegion>` (unquoted)?
- Does the transformed output match S3 event notification format?
- Are all required S3 event fields present?

### Phase 5: Target Configuration
- [ ] Set SNS topic as target for EventBridge rule
- [ ] Apply IAM permissions to SNS topic
- [ ] Verify EventBridge can publish to SNS

#### Issues to Check:
- Documentation shows IAM policy but doesn't explain WHERE to apply it
- Is it an SNS topic policy or IAM role policy?
- Does the policy need the specific rule ARN?

### Phase 6: Quilt Configuration
- [ ] Access Quilt Admin Panel
- [ ] Add/modify bucket configuration
- [ ] Set SNS topic ARN
- [ ] Disable direct S3 notifications (how?)

#### Issues to Check:
- Where exactly is the "disable S3 notifications" option?
- What if S3 notifications were never enabled?
- Screenshot/detailed instructions needed?

### Phase 7: Initial Indexing
- [ ] Trigger re-index without "Repair"
- [ ] Monitor indexing progress

#### Issues to Check:
- Where is the re-index option?
- What does "without Repair" mean?

### Phase 8: End-to-End Testing
- [ ] Upload test file to S3
- [ ] Check CloudTrail for event
- [ ] Check EventBridge metrics
- [ ] Check SNS metrics
- [ ] Check Quilt catalog for file

#### Event Flow to Verify:
1. S3 PutObject operation
2. CloudTrail captures event
3. EventBridge rule matches event
4. Input transformer converts format
5. SNS receives transformed event
6. Quilt processes event
7. File appears in catalog

## Known Gaps in Documentation

### Missing Information
1. **CloudTrail Setup**: No instructions for setting up CloudTrail if not already enabled
2. **IAM Policy Application**: Unclear where to apply the SNS policy (resource policy vs. identity policy)
3. **S3 Event Format**: No reference to what complete S3 event format should look like
4. **Error Debugging**: No troubleshooting steps if events don't flow
5. **Testing Tools**: No mention of using EventBridge test event feature

### Ambiguous Instructions
1. "Verify CloudTrail configuration" - how?
2. "Disable direct S3 Event Notifications" - where is this setting?
3. "Re-index bucket without Repair option" - what does Repair mean?

### Potential Technical Issues
1. **Input Transformer Syntax**: The `<variable>` syntax in template needs verification
2. **Event Pattern**: May need adjustment for different S3 operations
3. **IAM Permissions**: May need additional permissions not documented
4. **CloudTrail Delay**: Events may take time to appear (not mentioned)

## Test Results

### Environment Details
- AWS Region:
- Bucket Name:
- CloudTrail Name:
- SNS Topic ARN:
- EventBridge Rule ARN:
- Quilt Version:

### Test Execution Log
(To be filled in during testing)

### Issues Discovered
(To be filled in during testing)

### Recommended Documentation Fixes
(To be filled in after testing)
