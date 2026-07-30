# How do I collect search-cluster diagnostics for Quilt support?

## Tags

`aws`, `elasticsearch`, `opensearch`, `search`, `vpc`, `cloudshell`, `diagnostics`, `troubleshooting`

## Summary

When you report search-related issues (slow or failing searches, incomplete results, high cluster CPU), Quilt support may ask you to collect diagnostics from your deployment's Elasticsearch/OpenSearch domain. In most Quilt deployments the domain is VPC-internal, so the diagnostics must be collected from inside the Quilt stack's VPC. This article shows how to do that with an AWS CloudShell VPC environment and a short read-only script — no software installation required.

---

## What you'll collect

Four files describing shard layout, index sizes, disk allocation, and index settings:

- `cat_shards.txt`
- `cat_indices.txt`
- `cat_allocation.txt`
- `settings.json`

They contain index names (which mirror your registered bucket names), document counts, shard and disk statistics, and index configuration — no object contents, document data, or credentials.

## Step 1 — Check your credentials

The credentials you'll use — in CloudShell, the console role you're signed in with — need:

- `es:ESHttpGet` on the domain — the diagnostic requests (Step 4) are all read-only GETs
- `es:ListDomainNames` and `es:DescribeDomain` — for Step 2
- write access to some S3 bucket — for copying the results out (Step 5)

Check whether your existing role already allows these before granting anything new.

## Step 2 — Find your domain and endpoint

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

## Step 3 — Open a shell inside the stack VPC

The domain only accepts connections from members of one security group in your Quilt stack: `…SearchClusterAccessorSecurityGroup…`. Find it in the EC2 console by its description — *"For resources that need access to search cluster"* — or in the CloudFormation stack's Resources tab under the logical ID `SearchClusterAccessorSecurityGroup`.

(CloudShell isn't mandatory: any host inside the stack VPC with that security group and the Step 1 credentials can run the Step 4 script — Step 5 and Cleanup then don't apply. The path below uses CloudShell, which works even in a VPC with no internet access.)

In **CloudShell** (in your stack's region), create a new **VPC environment**. Two constraints to know before creating: you can have at most **two** VPC environments per user, and an environment's network settings can't be changed after creation — delete and recreate instead. (Creating one also needs CloudShell and EC2-describe permissions, beyond Step 1's list.) Fill in:

- **VPC**: the `vpc` value from Step 2.
- **Subnet**: any subnet in the VPC can reach the domain. Step 5 additionally needs a route to S3 — in a Quilt-created VPC every subnet has one (S3 gateway endpoint), so pick any; in a customer-managed VPC prefer a subnet that can reach S3 through an S3 gateway endpoint, NAT, or your network's usual egress path (e.g. Transit Gateway).
- **Security group**: the one from above.

Provisioning takes a minute or two; you're ready when the new environment opens with a shell prompt.

## Step 4 — Collect the diagnostics

Requests to the domain must be SigV4-signed; the script below signs them with your session's credentials using CloudShell's preinstalled Python and boto3. The request paths are fixed: AWS-managed domains only accept an allowlisted subset of the Elasticsearch REST API (for example, `/_all/_settings` is allowed but bare `/_settings` is rejected).

Fill in the two placeholders — `<VPC_ENDPOINT>` is the `endpoint` value from Step 2, pasted as-is (no `https://` prefix); `<REGION>` is your stack's region, as in Step 2 — then paste the whole block:

```bash
python3 << 'EOF'
import boto3, urllib3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

HOST = "<VPC_ENDPOINT>"
REGION = "<REGION>"

FILES = {
    "cat_shards.txt": "/_cat/shards?v=true",
    "cat_indices.txt": "/_cat/indices?v=true",
    "cat_allocation.txt": "/_cat/allocation?v=true",
    "settings.json": "/_all/_settings?flat_settings=true",
}
creds = boto3.Session().get_credentials().get_frozen_credentials()
http = urllib3.PoolManager()
for fname, path in FILES.items():
    url = "https://" + HOST + path
    req = AWSRequest(method="GET", url=url)
    SigV4Auth(creds, "es", REGION).add_auth(req)
    r = http.request("GET", url, headers=dict(req.headers))
    open(fname, "wb").write(r.data)
    print(fname, "HTTP", r.status)
EOF
```

Every line of output should end in `HTTP 200`:

```text
cat_shards.txt HTTP 200
cat_indices.txt HTTP 200
cat_allocation.txt HTTP 200
settings.json HTTP 200
```

Any other status means that request failed and its file contains the error message instead of data — see Troubleshooting.

## Step 5 — Copy the files out

CloudShell VPC environments can't use the console's upload/download menu, and their storage is **deleted when the session ends** — so move the files to S3 right away:

```bash
aws s3 cp cat_shards.txt s3://<your-bucket>/search-diagnostics/
aws s3 cp cat_indices.txt s3://<your-bucket>/search-diagnostics/
aws s3 cp cat_allocation.txt s3://<your-bucket>/search-diagnostics/
aws s3 cp settings.json s3://<your-bucket>/search-diagnostics/
```

Use any bucket you can write to, then download the files from the S3 console.

## Step 6 — Send the files

Attach the four files (plus the engine version from Step 2) to your support thread or email them to support@quilt.bio.

## Cleanup

Delete the CloudShell VPC environment when you're done — it otherwise keeps network interfaces in your VPC.

## Troubleshooting

- **`HTTP 403`** — the credentials lack `es:ESHttpGet` on the domain (Step 1).
- **`HTTP 401` with `"Your request … is not allowed"`** — the URL path isn't on AWS's supported-operations allowlist for managed domains; use the script exactly as given above.
- **The script hangs, then times out** — the environment isn't in the stack VPC, or is missing the `SearchClusterAccessorSecurityGroup`.
- **`aws s3 cp` hangs or fails** — the subnet has no route to S3; recreate the environment in a subnet that has one (see the subnet guidance in Step 3).
