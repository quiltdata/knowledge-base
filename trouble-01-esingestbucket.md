# Depoying Quilt Release 1.61.0 fails with "Bucket name should not contain uppercase characters" when stack has UpperCaseName

## Tags

`aws`, `cdk`, `s3`, `bucket`, `naming`, `cloudformation`, `deployment`

## Summary

Attempts to deploy Quilt Release 1.61 fails when creating EsIngestBucket due, to uppercase characters in the CloudFormation stack name being used in S3 bucket naming, violating AWS S3 bucket naming requirements. Workaround is to switch to a lowercase stack name.

---

## Symptoms

- CDK deployment fails during stack update/creation with S3 bucket creation error
- Error message: "Bucket name should not contain uppercase characters"
- Stack enters UPDATE_ROLLBACK_FAILED state
- EsIngestBucket resource specifically fails to create

## Root Cause

- EsIngestBucket uses explicit bucket naming pattern: `${AWS::StackName}-${AWS::Region}-esingestbucket`
- When CloudFormation stack name contains uppercase characters, resulting bucket name violates AWS S3 naming rules
- S3 bucket names must be lowercase and follow DNS naming conventions

**Why explicit naming is required:**

- Bucket name must be known at template creation time for SQS queue policy conditions
- CloudFormation requires deterministic naming for cross-resource references
- Multiple stacks in same account/region need unique bucket names

## Recommended Workaround

Use lowercase CloudFormation stack name, then retry installation.

If this is not feasible for you, please [contact support](mailto:support@quilt.bio).
