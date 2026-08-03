# How do I collect search-cluster diagnostics for Quilt support?

## Tags

`aws`, `elasticsearch`, `opensearch`, `search`, `vpc`, `cloudshell`, `cloudwatch`, `diagnostics`, `troubleshooting`

## Summary

When you report search-related issues (slow or failing searches, incomplete results, high cluster CPU), Quilt support may ask for diagnostics from your deployment's Elasticsearch/OpenSearch domain: CloudWatch performance metrics, plus cluster-state files collected from inside the stack's VPC (the domain is VPC-internal in most deployments). This article shows how to do both with AWS CloudShell and a short read-only script — no software installation required. You'll work in two shells: a **standard CloudShell** for the performance metrics (Step 3), and a **CloudShell VPC environment** for the cluster state (Steps 4–6).

The collected files disclose your registered bucket names (as index names), but no object contents, document data, or credentials.

---

## Step 1 — Check your credentials

The credentials you'll use — in CloudShell, the console role you're signed in with — need:

- `es:ListDomainNames` and `es:DescribeDomain` — for Step 2
- `cloudwatch:GetMetricStatistics` — for Step 3
- permission to create and use CloudShell VPC environments ([AWS's required IAM permissions](https://docs.aws.amazon.com/cloudshell/latest/userguide/sec-auth-with-identities.html)) — for Step 4 (this creates no infrastructure — see the note there)
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

**If `endpoint` is null**, your domain has a public endpoint instead — read it from `DomainStatus.Endpoint`. Public-endpoint deployments skip Steps 4 and 6: run the Step 5 script from any shell, with the public endpoint as `HOST` — the files land wherever you run it.

## Step 3 — Export CloudWatch metrics

This step needs no VPC access — run it in a standard CloudShell (or any shell with the AWS CLI). Fill in the two variables at the top:

```bash
REGION=<REGION>
DOMAIN=<DOMAIN_NAME>
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
START=$(($(date +%s) - 7*86400))
END=$(date +%s)

for m in CPUUtilization SearchLatency IndexingLatency SearchRate IndexingRate \
         JVMMemoryPressure ThreadpoolSearchQueue ThreadpoolSearchRejected \
         ThreadpoolWriteQueue ThreadpoolWriteRejected CoordinatingWriteRejected \
         PrimaryWriteRejected ReplicaWriteRejected ClusterIndexWritesBlocked FreeStorageSpace; do
  aws cloudwatch get-metric-statistics --region $REGION --namespace AWS/ES \
    --metric-name $m --dimensions Name=DomainName,Value=$DOMAIN Name=ClientId,Value=$ACCOUNT \
    --start-time $START --end-time $END --period 600 --statistics Average Maximum \
    > "cw_$m.json"
  echo "cw_$m.json"
done
```

This exports the last 7 days at 10-minute resolution (support may ask for a different window). Each file should contain a `Datapoints` array with roughly a thousand entries. Empty arrays in **every** file mean a wrong `DOMAIN`, `ACCOUNT`, or region; a few empty files are normal (not every metric exists on every engine version).

In a standard CloudShell you can download the files directly: **Actions → Download file**. (Or `aws s3 cp` them to the same bucket you'll use in Step 6.)

## Step 4 — Open a shell inside the stack VPC

The domain only accepts connections from members of one security group in your Quilt deployment — the **accessor security group**. Find it in the EC2 console by its description — *"For resources that need access to search cluster"* — or by name (it contains `SearchClusterAccessorSecurityGroup`). Or from any shell (`<VPC_ID>` is the `vpc` value from Step 2):

```bash
aws ec2 describe-security-groups --region <REGION> \
  --filters Name=vpc-id,Values=<VPC_ID> \
  --query "SecurityGroups[?contains(Description, 'access to search cluster')].[GroupId,GroupName]" \
  --output text
```

In **CloudShell** (in your stack's region), create a new **VPC environment** ([AWS walkthrough](https://docs.aws.amazon.com/cloudshell/latest/userguide/creating-vpc-environment.html)). Despite the "create", this is not new infrastructure — not a VPC endpoint, not an instance: a VPC environment is an ordinary CloudShell session whose network interface sits inside your VPC. It changes nothing in your Quilt deployment, costs nothing, and deleting it (see Cleanup) removes everything it made.

Before creating, know two constraints: at most **two** VPC environments per IAM principal — shared with anyone else using the same role — so delete one if you're at the limit; and network settings are fixed at creation, so to change them you delete and recreate. Fill in:

- **VPC**: the `vpc` value from Step 2.
- **Subnet**: pick a subnet the Quilt services run on — in a Quilt-created VPC, one named `<stack>-private-…`; if you supplied your own VPC, one of the stack's `Subnets` parameter values. Any subnet can reach the domain (access is gated by the security group), but Step 6 copies the files out via S3, and **the domain's own subnets often can't reach S3** — in newer deployments they're deliberately isolated. The worst a wrong pick does is make Step 6 hang; recreating the environment with another subnet fixes it.
- **Security group**: the accessor security group from above.

Provisioning takes a minute or two; you're ready when the new environment opens with a shell prompt.

## Step 5 — Collect the cluster state

Back in the **VPC environment** from Step 4: requests to the domain must be SigV4-signed, and the script below signs them with your session's credentials using CloudShell's preinstalled Python and boto3. The request paths are fixed — AWS-managed domains accept only an allowlisted subset of the domain's REST API.

Fill in the two placeholders — `<VPC_ENDPOINT>` is the `endpoint` value from Step 2 (no `https://` prefix); `<REGION>` as before — then paste the whole block:

```bash
python3 << 'EOF'
# A VPC-internal domain is reachable ONLY from the CloudShell VPC environment
# from Step 4 — anywhere else, every request fails. (Public endpoint: any shell.)
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
http = urllib3.PoolManager(timeout=urllib3.Timeout(connect=10, read=None), retries=False)
for fname, path in FILES.items():
    url = "https://" + HOST + path
    req = AWSRequest(method="GET", url=url)
    SigV4Auth(creds, "es", REGION).add_auth(req)
    try:
        r = http.request("GET", url, headers=dict(req.headers))
    except urllib3.exceptions.HTTPError as e:
        raise SystemExit(
            f"{type(e).__name__}: cannot reach {HOST} from this shell.\n"
            "Not a script problem. VPC-internal domain: run this, unmodified, "
            "in the CloudShell VPC environment from Step 4. "
            "Public endpoint: check the HOST value."
        )
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

CloudShell VPC environments can't use the console's upload/download menu, and their storage is **deleted when the session ends**, and idle sessions end after 20–30 minutes (10 in GovCloud) — so move the files to S3 right away:

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

Delete the CloudShell VPC environment when you're done — it otherwise keeps network interfaces in your VPC. If the delete leaves a network interface behind (your role lacks `ec2:DeleteNetworkInterface`), remove it in the EC2 console. Once support confirms it has the files, you can also delete the `search-diagnostics/` copies from your bucket.

## Troubleshooting

- **Every `cw_*.json` file has an empty `Datapoints` array** (Step 3) — wrong `DOMAIN`, `ACCOUNT`, or region in the variables (a few empty files are normal).
- **`cannot reach …` (`ConnectTimeoutError`, `NewConnectionError`), `Max retries exceeded`, or a silent hang** (Step 5) — the shell has no network path to the domain: you're not in the VPC environment from Step 4, or it's missing the accessor security group. This is a network-placement problem, not a script bug — modifying the script won't help; fix the environment and rerun the script unmodified.
- **`HTTP 403`** (Step 5) — the credentials lack `es:ESHttpGet` on the domain (Step 1).
- **`HTTP 401` with `"Your request … is not allowed"`** (Step 5) — the URL path isn't on AWS's supported-operations allowlist for managed domains; use the script exactly as given above.
- **`aws s3 cp` hangs or fails** (Step 6) — the subnet has no route to S3 (the domain's own subnets often don't); delete the environment and recreate it in a subnet that has one — see the subnet guidance in Step 4.
