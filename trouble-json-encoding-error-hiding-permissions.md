# JSON Encoding Error Masking Underlying Permission Issues

## Tags

`permissions`, `iam`, `s3`, `error-handling`, `debugging`, `s3-proxy`, `troubleshooting`

## Summary

When S3 permission errors (e.g., `AccessDenied`) occur, the error response from AWS is XML-formatted. In some code paths, attempts to parse this as JSON result in a `JSONDecodeError`, which masks the original permission error and makes debugging more difficult.

---

## Symptoms

- **Generic error messages instead of permission errors**
  - Error: `JSONDecodeError: Expecting value...` or `Invalid JSON`
  - The underlying `AccessDenied` or `Forbidden` error is not visible

- **Confusing error logs**
  - Logs show JSON parsing failures
  - No clear indication that the root cause is a missing IAM permission

- **Operations fail without clear reason**
  - Package downloads fail
  - Bucket operations time out or return errors
  - S3 proxy returns non-descriptive errors

## Likely Causes

### 1. AWS S3 Returns XML Error Responses

AWS S3 returns error responses in XML format:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Error>
    <Code>AccessDenied</Code>
    <Message>Access Denied</Message>
    <RequestId>...</RequestId>
    <HostId>...</HostId>
</Error>
```

When application code expects JSON and attempts to parse this response:

```python
response_data = json.loads(response.text)  # Raises JSONDecodeError
```

The original error information is lost in the exception handling.

### 2. Missing IAM Permissions

Common permission issues that trigger this:

- **S3 bucket policy denying access**
  - VPC endpoint policies too restrictive
  - Bucket policy not allowing the Quilt IAM roles
  
- **IAM role missing required permissions**
  - `s3:GetObject`, `s3:PutObject`, `s3:ListBucket` missing
  - Cross-account access not configured
  
- **Resource-based policies conflicting**
  - KMS key policies not allowing decrypt
  - SNS/SQS policies not allowing publish/receive

### 3. Error Handling Code Path

The error may occur in:

1. S3 proxy nginx → upstream registry → S3
2. Lambda functions processing S3 events
3. Registry API calling AWS services

## Recommendation

### Immediate Debugging Steps

#### 1. Check IAM Permissions

Review the IAM roles used by Quilt services:

| Role | Purpose |
|------|---------|
| `T4BucketReadRole` | Read access to managed buckets |
| `T4BucketWriteRole` | Write access to managed buckets |
| `PackagerRole` | Package operations |
| `ManagedUserRole` | User-assumed role for data access |

Verify these roles have the required permissions for your buckets.

#### 2. Test S3 Access Directly

Use AWS CLI with the Quilt role to test access:

```bash
# Get credentials from ECS task (if ECS Exec enabled)
aws sts get-caller-identity

# Test bucket access
aws s3 ls s3://YOUR_BUCKET/
aws s3 cp s3://YOUR_BUCKET/test-file.txt -
```

#### 3. Enable S3 Access Logging

Enable S3 server access logging to see the actual error codes returned by S3:

```bash
aws s3api put-bucket-logging \
  --bucket YOUR_BUCKET \
  --bucket-logging-status '{
    "LoggingEnabled": {
      "TargetBucket": "YOUR_LOG_BUCKET",
      "TargetPrefix": "s3-access-logs/"
    }
  }'
```

#### 4. Check CloudTrail

Look for `AccessDenied` events in CloudTrail:

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=GetObject \
  --max-items 50
```

Filter for events with `errorCode: AccessDenied`.

### Common Permission Fixes

#### Bucket Policy for Quilt Roles

Ensure your bucket policy allows Quilt roles:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowQuiltAccess",
      "Effect": "Allow",
      "Principal": {
        "AWS": [
          "arn:aws:iam::ACCOUNT:role/STACK-T4BucketReadRole-XXXX",
          "arn:aws:iam::ACCOUNT:role/STACK-T4BucketWriteRole-XXXX"
        ]
      },
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::YOUR_BUCKET",
        "arn:aws:s3:::YOUR_BUCKET/*"
      ]
    }
  ]
}
```

#### VPC Endpoint Policy

If using S3 VPC endpoints, ensure the endpoint policy allows access:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowAll",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": "*"
    }
  ]
}
```

Or restrict to specific principals/resources as needed.

#### Cross-Account Access

For cross-account bucket access, both the bucket policy AND the IAM role policy must allow access:

1. **Bucket policy** (in bucket account): Allow the Quilt role ARN
2. **IAM policy** (in Quilt account): Allow actions on the bucket ARN

### Future Improvement

We are tracking an enhancement to improve error handling so that:

1. Original AWS error messages are preserved and logged
2. XML error responses from S3 are properly parsed
3. Clear error messages distinguish between permission errors and other failures

## Debugging Steps

### 1. Enable Debug Logging

Set the `FLASK_DEBUG=1` environment variable in the registry container to get more detailed error messages.

### 2. Check Specific Error Logs

Look in CloudWatch Logs for patterns:

**S3 Proxy logs** (`/quilt/${StackName}/s3-proxy`):
```
# Look for upstream errors
upstream returned...
proxy_pass...error
```

**Registry logs** (`/quilt/${StackName}/registry`):
```
# Look for boto3/botocore errors
ClientError
AccessDenied
```

### 3. Reproduce with AWS CLI

Identify the exact operation failing and reproduce with AWS CLI using the same credentials.

## Related Issues

- DNS Resolution Issues with S3 Proxy (related KB article)
- [AWS S3 Error Responses](https://docs.aws.amazon.com/AmazonS3/latest/API/ErrorResponses.html)
- [IAM Policy Troubleshooting](https://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot_policies.html)
