# How do I collect search-cluster diagnostics for Quilt support?

## Tags

`aws`, `elasticsearch`, `opensearch`, `search`, `vpc`, `cloudshell`, `cloudwatch`, `diagnostics`, `troubleshooting`

## Summary

When you report search-related issues (slow or failing searches, incomplete results, high cluster CPU), Quilt support may ask for diagnostics from your deployment's Elasticsearch/OpenSearch domain: CloudWatch performance metrics, plus cluster-state files collected from inside the stack's VPC (the domain is VPC-internal in most deployments). This article shows how to do both with AWS CloudShell and a short read-only script — no software installation required.

---

## What you'll collect

You'll work in two shells: a **standard CloudShell** for the performance metrics (Step 3), and a **CloudShell VPC environment** for the cluster state (Steps 4–6).

Performance history — one JSON file per CloudWatch metric (CPU, search/indexing latency and rates, queues and rejections, JVM pressure, storage):

- `cw_<MetricName>.json` (12 files)

Cluster state — four files describing shard layout, index sizes, disk allocation, and index settings:

- `cat_shards.txt`
- `cat_indices.txt`
- `cat_allocation.txt`
- `settings.json`

Plus one line of text: the domain's engine version (from Step 2).

The files disclose your registered bucket names (as index names in the cluster-state files), but no object contents, document data, or credentials.

## Step 1 — Check your credentials

The credentials you'll use — in CloudShell, the console role you're signed in with — need:

- `es:ListDomainNames` and `es:DescribeDomain` — for Step 2
- `cloudwatch:GetMetricStatistics` — for Step 3
- permission to create and use CloudShell VPC environments ([AWS's required IAM permissions](https://docs.aws.amazon.com/cloudshell/latest/userguide/sec-auth-with-identities.html)) — for Step 4
- `es:ESHttpGet` on the domain — the cluster-state requests (Step 5) are all read-only GETs
- write access to some S3 bucket — for copying the results out (Step 6)

Check whether your existing role already allows these before granting anything new.

## Step 2 — Find your domain and endpoint

List the domains in your account (use your stack's region):

```bash
aws opensearch list-domain-names --region <REGION>
```

The Quilt search domain's name resembles your stack or deployment name — sometimes unchanged, sometimes lowercased, truncated, and suffixed (a stack named `Prod-QuiltDeploymentStack` gets a domain like `prod-qu-search-<random-suffix>`). Get its VPC endpoint, engine version, and VPC:

```bash
aws opensearch describe-domain --domain-name <DOMAIN_NAME> --region <REGION> \
  --query 'DomainStatus.{endpoint:Endpoints.vpc,version:EngineVersion,vpc:VPCOptions.VPCId}'
```

Note all three — the endpoint and VPC are used below; include the engine version in what you send to support. If you run several Quilt stacks, the `vpc` value tells you which stack's VPC a domain belongs to.

(A null `endpoint` means the domain has a public endpoint instead — `DomainStatus.Endpoint`. Then skip Step 4, run the Step 5 script from any shell with that endpoint as `HOST`, and skip Step 6 — the files land wherever you ran the script.)

## Step 3 — Export CloudWatch metrics

This step needs no VPC access — run it in a standard CloudShell (or any Linux shell with the AWS CLI), **not** in the VPC environment you'll create in Step 4, which has no route to the CloudWatch API. Fill in the two variables at the top:

```bash
REGION=<REGION>
DOMAIN=<DOMAIN_NAME>
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
START=$(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ)
END=$(date -u +%Y-%m-%dT%H:%M:%SZ)

for m in CPUUtilization SearchLatency IndexingLatency SearchRate IndexingRate \
         JVMMemoryPressure ThreadpoolSearchQueue ThreadpoolSearchRejected \
         ThreadpoolWriteQueue ThreadpoolWriteRejected ClusterIndexWritesBlocked FreeStorageSpace; do
  aws cloudwatch get-metric-statistics --region $REGION --namespace AWS/ES \
    --metric-name $m --dimensions Name=DomainName,Value=$DOMAIN Name=ClientId,Value=$ACCOUNT \
    --start-time $START --end-time $END --period 600 --statistics Average Maximum \
    > "cw_$m.json"
  echo "cw_$m.json"
done
```

This exports the last 7 days at 10-minute resolution (support may ask for a different window). Each file should contain a `Datapoints` array with several hundred entries — an empty array means a wrong `DOMAIN`, `ACCOUNT`, or region.

In a standard CloudShell you can download the files directly: **Actions → Download file**. (Or `aws s3 cp` them to the same bucket you'll use in Step 6.)

## Step 4 — Open a shell inside the stack VPC

The domain only accepts connections from members of one security group in your Quilt deployment. Find it in the EC2 console by its description — *"For resources that need access to search cluster"* — or by name: depending on how your deployment was created it contains `search-accessor` or `SearchClusterAccessorSecurityGroup`.

In **CloudShell** (in your stack's region), create a new **VPC environment** ([AWS walkthrough](https://docs.aws.amazon.com/cloudshell/latest/userguide/creating-vpc-environment.html)). Before creating, know: at most **two** VPC environments per user (delete one if you're at the limit), and network settings are fixed at creation — delete and recreate to change them. Fill in:

- **VPC**: the `vpc` value from Step 2.
- **Subnet**: any subnet reaches the domain, but Step 6 needs an S3 route from it — an S3 gateway endpoint in the subnet's route table, NAT, or your usual egress path (e.g. Transit Gateway). In Quilt-created VPCs every subnet typically qualifies.
- **Security group**: the one from above.

Provisioning takes a minute or two; you're ready when the new environment opens with a shell prompt.

## Step 5 — Collect the cluster state

Back in the **VPC environment** from Step 4: requests to the domain must be SigV4-signed, and the script below signs them with your session's credentials using CloudShell's preinstalled Python and boto3. The request paths are fixed — AWS-managed domains accept only an allowlisted subset of the domain's REST API.

Fill in the two placeholders — `<VPC_ENDPOINT>` is the `endpoint` value from Step 2 (no `https://` prefix); `<REGION>` as before — then paste the whole block:

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

## Step 6 — Copy the cluster-state files out

CloudShell VPC environments can't use the console's upload/download menu, and their storage is **deleted when the session ends** — so move the files to S3 right away:

```bash
aws s3 cp cat_shards.txt s3://<BUCKET>/search-diagnostics/
aws s3 cp cat_indices.txt s3://<BUCKET>/search-diagnostics/
aws s3 cp cat_allocation.txt s3://<BUCKET>/search-diagnostics/
aws s3 cp settings.json s3://<BUCKET>/search-diagnostics/
```

Use any bucket you can write to, then download the files from the S3 console.

## Step 7 — Send the files

Attach everything — the `cw_*.json` metric exports, the four cluster-state files, and the engine version from Step 2 — to your support thread or email them to support@quilt.bio.

## Cleanup

Delete the CloudShell VPC environment when you're done — it otherwise keeps network interfaces in your VPC.

## Troubleshooting

- **A `cw_*.json` file has an empty `Datapoints` array** (Step 3) — wrong `DOMAIN`, `ACCOUNT`, or region in the variables.
- **The script hangs, then times out** (Step 5) — the environment isn't in the stack VPC, or is missing the accessor security group from Step 4.
- **`HTTP 403`** (Step 5) — the credentials lack `es:ESHttpGet` on the domain (Step 1).
- **`HTTP 401` with `"Your request … is not allowed"`** (Step 5) — the URL path isn't on AWS's supported-operations allowlist for managed domains; use the script exactly as given above.
- **`aws s3 cp` hangs or fails** (Step 6) — the subnet has no route to S3; recreate the environment in a subnet that has one (see the subnet guidance in Step 4).
