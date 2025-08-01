# Retrospective: CDK Deployment Failure - Uppercase Bucket Name Issue

**Date:** August 1, 2025  
**Incident:** CDK deployment failed with "Bucket name should not contain uppercase characters"  
**Duration:** Deployment blocked until resolution  
**Impact:** Minimal: customers with uppercase stack name cannot experiment with new features, unless they change their stack names

## Summary

A CDK deployment to production failed due to an S3 bucket naming violation. The `EsIngestBucket` resource failed to create because its name contained uppercase characters from the CloudFormation stack name, violating AWS S3 bucket naming requirements.

## Timeline

- **July 24, 2025:** `EsIngestBucket` feature added in commit `19d2f72a` (PR #2084) by Alexei Mochalov
- **July 31, 2025:** Release 1.61 sent to customers
- **August 1, 2025 19:11 UTC:** CDK deployment initiated for QuiltStack
- **August 1, 2025 19:13 UTC:** Deployment failed during bucket creation
- **August 1, 2025:** Issue investigation and root cause analysis

## Root Cause

### Primary Issue

The `EsIngestBucket` uses an explicit bucket name that includes the CloudFormation stack name:

```python
BucketName = Sub("${AWS::StackName}-${AWS::Region}-esingestbucket")
```

When the stack name is, e.g., `QuiltStack`, the resulting bucket name becomes `QuiltStack-us-east-1-esingestbucket`, which contains uppercase letters (`Q` and `S`) that violate AWS S3 bucket naming requirements.

### Why Explicit Naming Was Required

Per the code comment and GitHub issue reference:

- The bucket name must be explicitly set because it's referenced in the SQS queue policy condition
- CloudFormation requires the bucket name to be known at template creation time
- See: <https://github.com/aws-cloudformation/cloudformation-coverage-roadmap/issues/79>

Because we (and potentially customers) can have multiple stacks in the same account and region, we need a unique but deterministic name
for such buckets.  And there do not seem to be any other gauranteed stack-unique identifiers we can use.

### Why Other Buckets Don't Have This Issue

Analysis of the codebase revealed that all other S3 buckets use auto-generated names (no `BucketName` parameter), allowing CloudFormation to create valid, unique names automatically. The `EsIngestBucket` is the only bucket requiring an explicit name due to its integration with SQS queue policies.

## Technical Details

### Error Message

```log
Resource handler returned message: "Bucket name should not contain uppercase characters" 
(RequestToken: fe351d2c-9eff-2aa2-a6a4-2e357059f731, HandlerErrorCode: GeneralServiceException)
```

### CloudFormation Limitations

- No built-in functions to convert strings to lowercase (`Fn::Lower` doesn't exist)
- No `AWS::CloudFormation::Transform` for string manipulation
- Cannot validate stack name format in CloudFormation templates
- `AWS::StackName` pseudo parameter cannot be modified at deployment time

### Failed Resources

- `EsIngestBucket` (primary failure)
- `DB` (failed due to concurrent engine upgrade)  
- `SearchHandlerRole` (failed due to dependency)

## Investigation Process

1. **Initial Assessment:** Reviewed deployment logs showing bucket creation failure
2. **Code Analysis:** Located bucket naming logic in `t4/template/search.py:427`
3. **Pattern Analysis:** Compared with other bucket creation patterns in codebase
4. **Git Blame:** Identified recent addition (July 24, 2025) in commit `19d2f72a`
5. **CloudFormation Research:** Confirmed lack of string manipulation capabilities

## Potential Solutions Evaluated

### Option 1: CloudFormation Template Validation

- **Pros:** Pure template solution
- **Cons:** CF cannot validate stack name format or convert case
- **Verdict:** Not technically feasible

### Option 2: Alternative Unique Identifiers

- Use `AWS::AccountId` + `AWS::Region` only
- **Pros:** Guaranteed lowercase
- **Cons:** Not unique across multiple stacks in same account/region
- **Verdict:** Insufficient for multi-stack environments

### Option 3: Custom CloudFormation Macro

- **Pros:** Could handle string transformation
- **Cons:** Adds infrastructure complexity, not suitable for shipped templates
- **Verdict:** Over-engineered for the problem

### Option 4: Documentation-Based Solution

- Document requirement for lowercase stack names
- **Pros:** Simple, no code changes
- **Cons:** Relies on user compliance, poor user experience
- **Verdict:** Acceptable but suboptimal

### Option 5: Require Extra lowercase identifier for multi-stack deployment

If uppercase names are MORE common that multi-stack deployments in the same account/region,
AND it is painful for customers to change an existing StackName,
we could change the policy to:

- Not use the stack name
- Use an extra parameter which *should* be lowercase

Then, the first deployment will always succeed.
If other co-located stacks fail, the customer can specify the `unique-stack-identifier` to ensure that succeeds.

## Lessons Learned

### What Went Well

- Clear error message from AWS made root cause identification straightforward
- Systematic code analysis quickly identified the unique naming pattern
- Git blame provided context about recent changes

### What Could Be Improved

- **Testing Coverage:** New features should be tested with realistic stack names (including uppercase)
- **Code Review:** S3 bucket naming patterns should be flagged for review
- **Documentation:** CloudFormation limitations should be better documented for developers
- **Code Freeze:** This functionality was added at the last minute, which hindered review and testing.

### Process Gaps

- No validation that new S3 buckets follow existing naming patterns
- Insufficient integration testing with various stack name formats
- Missing documentation about AWS resource naming constraints

## References

- **Commit:** `19d2f72a20e0d00f1990ddffbf46fd6deeb9958c`
- **PR:** #2084 "BSQIK"
- **CloudFormation Issue:** <https://github.com/aws-cloudformation/cloudformation-coverage-roadmap/issues/79>
- **AWS S3 Naming Rules:** [S3 Bucket Naming Guidelines](https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html)

---

*This retrospective was generated to document the investigation and resolution of the uppercase bucket naming failure encountered during CDK deployment on August 1, 2025.*
