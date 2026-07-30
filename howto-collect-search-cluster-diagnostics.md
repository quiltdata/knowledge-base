# How do I collect search-cluster diagnostics for Quilt support?

## Tags

`aws`, `elasticsearch`, `opensearch`, `search`, `vpc`, `cloudshell`, `diagnostics`, `troubleshooting`

## Summary

When you report search-related issues (slow or failing searches, incomplete results, high cluster CPU), Quilt support may ask you to collect diagnostics from your deployment's Elasticsearch/OpenSearch domain. In most Quilt deployments the domain is VPC-internal, so the four read-only diagnostic commands must run from a host inside the Quilt stack's VPC — an existing instance, or an AWS CloudShell VPC environment — using SigV4-signed requests via `awscurl`.

---

## What you'll collect

Four files describing shard layout, index sizes, disk allocation, and index settings:

- `cat_shards.txt`
- `cat_indices.txt`
- `cat_allocation.txt`
- `settings.json`

## Step 1 — Find your domain and endpoint

List the domains in your account (use your stack's region):

```bash
aws opensearch list-domain-names
```

Your Quilt search domain's name starts with your CloudFormation stack name (e.g. `prod-qu-search-…`). Get its VPC endpoint and engine version:

```bash
aws opensearch describe-domain --domain-name <DOMAIN_NAME> \
  --query 'DomainStatus.{endpoint:Endpoints.vpc,version:EngineVersion}'
```

Note both — include the engine version in what you send to support.

## Step 2 — Get a shell inside the stack VPC

The host needs two security groups from your Quilt stack:

- **`…SearchClusterAccessorSecurityGroup…`** — the domain only accepts connections (port 443) from members of this group. Find it in the EC2 console by its description: *"For resources that need access to search cluster"*, or in the CloudFormation stack's Resources tab under the logical ID `SearchClusterAccessorSecurityGroup`.
- **`…OutboundSecurityGroup…`** — general outbound access, needed to install tooling.

### Option A — an existing host in the stack VPC

If you already have a bastion/EC2 instance in the Quilt stack's VPC, attach the two security groups above to it and skip to Step 3.

### Option B — AWS CloudShell VPC environment

1. Open **CloudShell** in the AWS console (in your stack's region) and create a new **VPC environment**.
2. **VPC**: your Quilt stack's VPC.
3. **Subnet**: a **private subnet with a NAT route** to the internet. Do not pick an isolated subnet (in Quilt network-2.0 deployments the domain itself lives in isolated "intra" subnets — those have no internet access, and `pip install` will hang there). The subnet does not need to be the domain's own subnet; any subnet in the VPC can reach it.
4. **Security groups**: the two groups from above.

## Step 3 — Credentials

Your shell's AWS credentials (in CloudShell, the console role you're signed in with) need the `es:ESHttp*` permission on the domain. Administrator roles typically have this.

## Step 4 — Collect the diagnostics

Requests to the domain must be SigV4-signed; [`awscurl`](https://github.com/okigan/awscurl) handles that:

```bash
pip3 install --user awscurl
export PATH="$HOME/.local/bin:$PATH"
```

Then (fill in your endpoint and region):

```bash
ES=https://<VPC_ENDPOINT>
REGION=<REGION>

awscurl --service es --region $REGION "$ES/_cat/shards?v=true"                  > cat_shards.txt
awscurl --service es --region $REGION "$ES/_cat/indices?v=true"                 > cat_indices.txt
awscurl --service es --region $REGION "$ES/_cat/allocation?v=true"              > cat_allocation.txt
awscurl --service es --region $REGION "$ES/_all/_settings?flat_settings=true"   > settings.json
```

Use the commands exactly as written: AWS-managed domains only accept an allowlisted subset of the Elasticsearch REST API (for example, `/_all/_settings` is allowed but bare `/_settings` is rejected).

## Step 5 — Send the files

Attach the four files (plus the engine version from Step 1) to your support thread or email them to support@quilt.bio.

## Troubleshooting

- **`403`** — the credentials lack `es:ESHttp*` on the domain (Step 3), or the request isn't signed (plain `curl` won't work).
- **`401` `"Your request … is not allowed"`** — the URL path isn't on AWS's supported-operations allowlist for managed domains; use the commands exactly as given above.
- **Connection timeout** — the host isn't in the stack VPC, or is missing the `SearchClusterAccessorSecurityGroup`.
- **`pip install` hangs** — the subnet has no internet route; pick a NAT-routed private subnet (Option B, point 3).
