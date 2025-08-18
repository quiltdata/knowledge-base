# How-To: Validate my new/updated Quilt Catalog is correctly configured

## Tags

`quilt`, `catalog`, `validation`, `install`, `stack`, `ui`, `s3`

## Summary

**5-minute smoke test** for new Quilt Catalog stack installation, focusing on core UI functionality, metadata tagging, versioning, and search. Uses prepared test data for quick copy-paste validation.

---

## When to Use This

- Just installed a new Quilt stack, and want to ensure everything works
- Modified your stack or network/security configurations, and want to verify nothing broke
- Users report intermittent errors, and want to identify potential root causes

## Recommendation

Follow this **5-minute smoke test** to quickly validate core Quilt Catalog functionality. For comprehensive testing, use additional validation scripts.

## Prerequisites

- Test bucket: `mycompany-test-bucket` (or any existing S3 bucket)
- Test user email: `your-email+test@yourcompany.com` (Gmail alias for self-testing)
- Test data: Copy from `s3://quilt-example/examples/formats` to your bucket for diverse file format testing

---

### 5-Minute Smoke Test

#### 1. Login and User Management (1 min)

1. Go to your Quilt URL and log in
2. Click your user id (upper right) → Admin → Users and Roles → Users
3. Click "+" to add test user:
   - **Email:** `your-email+test@yourcompany.com`
   - **Role:** Editor
   - **Note:** Gmail aliases let you test with yourself
4. ✅ **Success:** You receive an invitation email

#### 2. Bucket Setup (30 sec)

1. Admin → Buckets → Click "+"
2. **Bucket Name:** `mycompany-test-bucket` (or your test bucket)
3. **Title:** `Smoke Test Bucket`
4. Click "Add"
5. Click Q logo (upper right) → Select the new bucket
6. ✅ **Success:** Overview page loads, tabs are clickable

#### 3. Copy Test Data & Create Package (2 min)

1. **Copy test data to your bucket:**

   ```bash
   aws s3 cp -r "s3://quilt-example/examples/formats/" s3://mycompany-test-bucket/examples/formats/
   ```

1. **Copy test metadtata to a local folder:**

   ```bash
   aws s3 cp -r "s3://quilt-example/examples/formats/" .
   ```

1. **Create package from copied data:**
   - Packages tab → "Create New Package"
   - Enter the package name `test/smoke`
   - Click "Add Files from Bucket"
   - Browse to `examples` -> `formats` in that `mycompany-test-bucket`
   - Click the upper-left square to select all the files
   - Click "Add Files"
   - Drag `iris.csv` local file from step 2 into the "Key | Value" metadata fields
   - Enter **Commit message:** `Smoke test package`
   - Click "Create"
2. ✅ **Success:** Package name shown in alert
   - Click on the resulting link
   - Verify files and metadata are show

1. ✅ **Success:** Package created, metadata visible

#### 4. Search Validation (1 min)

1. Search button (top bar) → Enter `smoke`
2. ✅ **Success:** Your package appears in results
3. Click package → Verify files are visible and readable

> **Combined test:** This validates package creation, indexing, search, and preview in one step.

#### 5. Query Test (30 sec)

1. Queries tab → Enter and run:

   ```sql
   SHOW TABLES
   ```

2. Look for `mycompany-test-bucket_packages-view`
3. **Quick metadata query:**

   ```sql
   SELECT *
   FROM "mycompany-test-bucket_packages-view"
   WHERE json_extract_scalar(user_meta, '$.test_type') = 'smoke_test'
   LIMIT 5
   ```

4. ✅ **Success:** Query returns your test package

---

## Smoke Test Complete

**Total time:** ~5 minutes  
**Validated:** Login, bucket access, package creation, search, and queries

### Next Steps

- For comprehensive testing, run detailed validation scripts
- Monitor logs for any warnings during testing
- Test additional file types and workflows as needed
