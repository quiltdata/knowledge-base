# DNS Resolution Issues with S3 Proxy in Private VPC Deployments

## Tags

`dns`, `s3-proxy`, `ecs`, `network`, `private-vpc`, `awsvpc`, `troubleshooting`

## Summary

When deploying Quilt in a private VPC with custom DNS configuration, the S3 proxy service may fail to resolve internal hostnames (including the internal registry and AWS S3 endpoints). This occurs because the s3-proxy container obtains its DNS resolver from `/etc/resolv.conf`, which may not include the AWS-provided DNS server (169.254.169.253 or VPC+2 address) when custom DHCP options are configured.

---

## Symptoms

- **S3 proxy fails to connect to the internal registry**
  - Error: `could not resolve internal registry hostname`
  - Downloads from the Quilt catalog fail
  - Package operations may time out

- **S3 proxy cannot resolve AWS S3 endpoints**
  - Requests to S3 buckets fail
  - Error logs show DNS resolution failures in nginx

- **Observable indicators:**
  - ECS task logs show nginx resolver errors
  - `502 Bad Gateway` errors in the catalog
  - Package downloads consistently fail while other Quilt functionality works

- **Common environment:**
  - Private VPC with custom DHCP options
  - On-premises DNS servers configured
  - VPN or Direct Connect to on-premises infrastructure
  - AWS-provided DNS (169.254.169.253) not included in DHCP options

## Likely Causes

### 1. Custom DHCP Options Excluding AWS DNS

When customers configure custom DHCP option sets for their VPC that specify on-premises DNS servers without including AWS's DNS resolver, ECS tasks running in `awsvpc` network mode will not have access to AWS's DNS.

The Quilt S3 proxy service uses nginx, which reads the nameserver from `/etc/resolv.conf` at startup:

```bash
# From s3-proxy/run-nginx.sh
nameserver=$(awk '{if ($1 == "nameserver") { print $2; exit;}}' < /etc/resolv.conf)
```

If this nameserver cannot resolve:
- Internal AWS hostnames (e.g., S3 VPC endpoint DNS names)
- Cloud Map service discovery names (e.g., `registry.${StackName}`)

Then the S3 proxy will fail.

### 2. VPC Endpoint Private DNS Not Resolving

Even with an S3 VPC endpoint configured, if the task's DNS resolver cannot reach AWS's DNS infrastructure, private DNS names for the endpoint won't resolve.

### 3. Service Discovery (Cloud Map) DNS Failures

Quilt uses AWS Cloud Map for internal service discovery. The registry service registers as `registry.${AWS::StackName}` in a private DNS namespace. Resolving this name requires access to the Route 53 Resolver (AWS DNS).

## Recommendation

### Immediate Fix: Add AWS DNS to DHCP Options

1. **Modify your VPC's DHCP option set** to include the AWS-provided DNS resolver alongside your custom DNS servers:

   **Option A**: Add `169.254.169.253` (works for EC2 instances)
   
   **Option B**: Add your VPC's DNS address at `<VPC_CIDR_BASE>+2` (e.g., `10.0.0.2` for a `10.0.0.0/16` VPC)

2. **Update the DHCP options** in AWS Console or via CLI:

   ```bash
   aws ec2 create-dhcp-options \
     --dhcp-configurations \
       "Key=domain-name-servers,Values=10.0.0.2,YOUR_CUSTOM_DNS_1,YOUR_CUSTOM_DNS_2"
   ```

3. **Associate the new DHCP options** with your VPC and restart ECS tasks to pick up the new configuration.

### Workaround: DNS Forwarding

If you cannot modify DHCP options, configure your on-premises DNS servers to forward queries for AWS domains to the AWS DNS resolver:

1. **Forward zones:**
   - `amazonaws.com`
   - `aws.amazon.com`
   - Your Cloud Map namespace (e.g., `your-stack-name`)

2. Configure conditional forwarding to the Route 53 Resolver inbound endpoint.

### Future Enhancement Request

The customer has requested the ability to specify custom DNS servers as a CloudFormation parameter. This would involve adding `DnsServers` to the ECS task definitions:

```yaml
# Example of desired functionality
Parameters:
  CustomDnsServers:
    Type: CommaDelimitedList
    Default: ""
    Description: "Custom DNS servers for ECS tasks (optional)"
```

This enhancement is being tracked internally.

## Debugging Steps

### 1. Verify DNS in the running container

If ECS Exec is enabled, connect to the s3-proxy container:

```bash
aws ecs execute-command \
  --cluster YOUR_CLUSTER \
  --task TASK_ID \
  --container s3-proxy \
  --command "/bin/sh" \
  --interactive
```

Then check:

```bash
cat /etc/resolv.conf
nslookup registry.YOUR_STACK_NAME
nslookup s3.us-east-1.amazonaws.com
```

### 2. Check CloudWatch Logs

Look for DNS resolution errors in the s3-proxy log group:

```
/quilt/${StackName}/s3-proxy
```

Common error patterns:
- `[error] ... could not be resolved`
- `upstream timed out`
- `no resolver defined to resolve`

### 3. Verify VPC DNS Settings

```bash
aws ec2 describe-vpc-attribute \
  --vpc-id YOUR_VPC_ID \
  --attribute enableDnsSupport

aws ec2 describe-vpc-attribute \
  --vpc-id YOUR_VPC_ID \
  --attribute enableDnsHostnames
```

Both should return `true`.

### 4. Check DHCP Options

```bash
aws ec2 describe-dhcp-options \
  --dhcp-options-ids $(aws ec2 describe-vpcs --vpc-ids YOUR_VPC_ID \
    --query 'Vpcs[0].DhcpOptionsId' --output text)
```

Verify that `domain-name-servers` includes an AWS DNS resolver.

## Related Issues

- [AWS Documentation: DNS attributes for your VPC](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-dns.html)
- [AWS Documentation: DHCP options sets](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_DHCP_Options.html)
- [ECS Task Networking with awsvpc mode](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-networking.html)

## See Also

- JSON Encoding Error Hiding Permission Issues (related KB article)
- Private VPC Deployment Best Practices
