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

They contain index names (which mirror your registered bucket names), document counts, shard and disk statistics, and index configuration — no object contents, document data, or credentials.

## Step 1 — Find your domain and endpoint

List the domains in your account (use your stack's region):

```bash
aws opensearch list-domain-names --region <REGION>
```

The search domain's name is derived from your CloudFormation stack name — lowercased and truncated — so a stack named `Prod-QuiltDeploymentStack` gets a domain like `prod-qu-search-<random-suffix>`. Get its VPC endpoint, engine version, and VPC:

```bash
aws opensearch describe-domain --domain-name <DOMAIN_NAME> --region <REGION> \
  --query 'DomainStatus.{endpoint:Endpoints.vpc,version:EngineVersion,vpc:VPCOptions.VPCId}'
```

Note all three — the endpoint and VPC are used below; include the engine version in what you send to support. If you run several Quilt stacks, the `vpc` value tells you which stack's VPC a domain belongs to.

## Step 2 — Get a shell inside the stack VPC

The host needs two security groups from your Quilt stack:

- **`…SearchClusterAccessorSecurityGroup…`** — the domain only accepts connections (port 443) from members of this group. Find it in the EC2 console by its description: *"For resources that need access to search cluster"*, or in the CloudFormation stack's Resources tab under the logical ID `SearchClusterAccessorSecurityGroup`.
- **`…OutboundSecurityGroup…`** — allows outbound HTTPS (port 443), needed to download tooling. Console description: *"Outbound HTTPS traffic to anywhere"*; logical ID `OutboundSecurityGroup`.

### Option A — an existing host in the stack VPC

If you already have a bastion/EC2 instance in the Quilt stack's VPC, attach the two security groups above to it and skip to Step 3. The instance needs `python3` and `pip3`, and its credentials (typically the instance profile) must carry the Step 3 permissions — default instance profiles usually don't.

### Option B — AWS CloudShell VPC environment

1. Open **CloudShell** in the AWS console (in your stack's region) and create a new **VPC environment**. Creating one needs CloudShell and EC2-describe permissions in addition to Step 3. You can have at most **two** VPC environments per user, and an environment's network settings can't be edited after creation — verify the subnet (next point) before creating.
2. **VPC**: the `vpc` value from Step 1.
3. **Subnet**: a **private subnet with a NAT route** — its route table should have a `0.0.0.0/0` route pointing at a NAT gateway (`nat-…`). Two choices that look plausible but fail: *isolated* subnets (no internet route at all — in Quilt network-2.0 deployments the domain's own "intra" subnets are like this, and `pip install` will hang there), and *public* subnets (CloudShell VPC environments get no public IP, so an internet-gateway route gives them no internet either). The subnet does not need to be the domain's own subnet; any subnet in the VPC can reach it.
4. **Security groups**: the two groups from above.

## Step 3 — Credentials

Your shell's AWS credentials (in CloudShell, the console role you're signed in with) need:

- `es:ESHttpGet` on the domain — the diagnostic requests below are all read-only GETs
- `es:ListDomainNames` and `es:DescribeDomain` — for Step 1

Check whether your existing role already allows these before granting anything new.

## Step 4 — Collect the diagnostics

Requests to the domain must be SigV4-signed; [`awscurl`](https://github.com/okigan/awscurl) handles that:

```bash
pip3 install --user awscurl
export PATH="$HOME/.local/bin:$PATH"
```

Then fill in your endpoint and region. `<VPC_ENDPOINT>` is the `endpoint` value from Step 1, which has no scheme prefix — the result should look like `ES=https://vpc-prod-qu-search-abc123.us-east-1.es.amazonaws.com`:

```bash
ES=https://<VPC_ENDPOINT>
REGION=<REGION>

awscurl --fail-with-body --service es --region $REGION "$ES/_cat/shards?v=true"                  > cat_shards.txt
awscurl --fail-with-body --service es --region $REGION "$ES/_cat/indices?v=true"                 > cat_indices.txt
awscurl --fail-with-body --service es --region $REGION "$ES/_cat/allocation?v=true"              > cat_allocation.txt
awscurl --fail-with-body --service es --region $REGION "$ES/_all/_settings?flat_settings=true"   > settings.json
```

Use the commands exactly as written: AWS-managed domains only accept an allowlisted subset of the Elasticsearch REST API (for example, `/_all/_settings` is allowed but bare `/_settings` is rejected).

Sanity-check the results — a failed command exits with an error status, and its output file then contains the error message instead of data:

```bash
head -2 cat_shards.txt cat_indices.txt cat_allocation.txt
head -c 100 settings.json; echo
```

The three `.txt` files should each show a column-header table (`index shard prirep state …`); `settings.json` should start with `{"<index-name>":…`. A file containing `{"Message": …}` means that request failed — see Troubleshooting.

## Step 5 — Copy the files off the host

CloudShell VPC environments can't use the console's upload/download menu, and their storage is **deleted when the session ends** — so move the files to S3 right away:

```bash
aws s3 cp cat_shards.txt s3://<your-bucket>/search-diagnostics/
aws s3 cp cat_indices.txt s3://<your-bucket>/search-diagnostics/
aws s3 cp cat_allocation.txt s3://<your-bucket>/search-diagnostics/
aws s3 cp settings.json s3://<your-bucket>/search-diagnostics/
```

Use any bucket you can write to, then download the files from the S3 console. On an Option A host, your usual file transfer (`scp`, SSM) works too.

## Step 6 — Send the files

Attach the four files (plus the engine version from Step 1) to your support thread or email them to support@quilt.bio.

## Cleanup

- **Option B**: delete the CloudShell VPC environment when you're done — it otherwise keeps network interfaces in your VPC.
- **Option A**: detach the two security groups from the instance; they're only needed while collecting.

## Troubleshooting

- **`403`** — the credentials lack `es:ESHttpGet` on the domain (Step 3), or the request isn't signed (plain `curl` won't work).
- **`401` `"Your request … is not allowed"`** — the URL path isn't on AWS's supported-operations allowlist for managed domains; use the commands exactly as given above.
- **Connection timeout** — the host isn't in the stack VPC, or is missing the `SearchClusterAccessorSecurityGroup`.
- **`pip install` hangs** — the subnet has no internet route; pick a NAT-routed private subnet (Option B, point 3).
