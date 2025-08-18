# How-To: Validate my new/updated Quilt Catalog is correctly configured

## Tags

`quilt`, `catalog`, `validation`, `install`, `stack`, `ui`, `s3`

## Summary

**5-minute smoke test** for new Quilt Catalog stack installation, focusing on core UI functionality, metadata tagging, versioning, and search. Uses prepared test data for quick validation.

---

## When to Use This

1. Just installed a new Quilt stack, and want to ensure everything works
1. Modified your stack or network/security configurations, and want to verify nothing broke
1. Users report intermittent errors, and want to identify potential root causes

## Prerequisites

- Quilt stack you can log into with Admin permissions
- Novel email that does not yet have an account: `your-email+test@yourcompany.com` (e.g., a Gmail +alias)
- New or existing S3 bucket with write access, not currently in the stack: `yourcompany-test-bucket`
- AWS credentials and the `aws` CLI available from a Terminal sessions

## 5-Minute Smoke Test

### 1. Login and User Management (1 min)

Test that when you add a new user, it triggers a password reset email.

1. Go to your Quilt URL and log in
2. Click your user id (upper right) → Admin → Users and Roles → Users
3. Click "+" to add test user:
   - **Email:** `your-email+test@yourcompany.com`
4. ✅ **Success:** You receive the invitation email

### 2. Bucket Setup (30 sec)

Test that you can add a bucket (easier if it is in the same account and region as your stack).

1. Admin → Buckets → Click "+"
2. **Bucket Name:** `yourcompany-test-bucket`
3. **Title:** `Smoke Test Bucket`
4. Click "Add"
5. Verify the Bucket add succeeded. If not, check the browser console.
6. Click Q logo (upper left) → Select the new bucket
7. ✅ **Success:** Overview page loads, tabs are clickable

NOTE: You can optionally skip this step and reuse an existing bucket for testing.

However, if you use it more than once, you would need to edit (or add to)
the example files in order to create a new package revisions.

### 3. Copy Test Data & Create Package (2 min)

1. **Copy test data to your bucket:**

   ```bash
   aws s3 cp -r "s3://quilt-example/examples/formats/" s3://yourcompany-test-bucket/examples/formats/
   ```

2. **Copy test metadata to a local folder:**

   ```bash
   aws s3 cp -r "s3://quilt-example/examples/formats/" .
   ```

3. **Create package from copied data:**
   - Packages tab → "Create New Package"
   - Enter the package name `test/smoke`
   - Click "Add Files from Bucket"
   - Browse to `examples` -> `formats` in `yourcompany-test-bucket`
   - Click the upper-left square to select all the files
   - Click "Add Files"
   - Drag `metadata.json` local file from step 2 into the "Key | Value" metadata fields
   - Enter **Commit message:** `Smoke test package`
   - Click "Create"
   - ✅ **Success:** Package name shown in alert
   - Click on the resulting link
   - Verify files and metadata are shown

4. ✅ **Success:** Package created, metadata visible

### 4. Search Validation (1 min)

1. Click Search button (top bar)
1. Enter `SMP001` in the search bar
1. ✅ **Success:** Your package `test/smoke` appears in results, along with that metadata
1. Click (card view) or scroll (table view) to find that metadata field

### 5. Query Test (30 sec)

1. Queries tab → Enter and run:

   ```sql
   SHOW TABLES
   ```

2. Look for `yourcompany-test-bucket_packages-view`
3. **Quick metadata query:**

   ```sql
   SELECT *
   FROM "yourcompany-test-bucket_packages-view"
   WHERE json_extract_scalar(user_meta, '$.sample_id') = 'SMP001'
   ```

4. ✅ **Success:** Query returns your test package

---

## Next Steps

- For comprehensive validation, define and run your own custom smoke tests
- Monitor logs for any warnings during testing
- Test additional file types and workflows as needed
