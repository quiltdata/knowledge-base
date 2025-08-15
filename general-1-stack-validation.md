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

- Test bucket: `quilt-smoke-test-bucket` (or any existing S3 bucket)
- Test user email: `smoketest@yourcompany.com`
- Test files: Download [sample-data.zip](https://open.quiltdata.com/b/quilt-example/packages/examples%2Fwellplates/latest) for quick testing

---

### 5-Minute Smoke Test

#### 1. Login and User Management (1 min)

1. Go to your Quilt URL and log in
2. Click your user id (upper right) → Admin → Users and Roles → Users
3. Click "+" to add test user:
   - **Email:** `smoketest@yourcompany.com`
   - **Role:** Editor
4. ✅ **Success:** User receives invitation email

> **Skip on failure:** Continue to next step if email issues occur.

#### 2. Bucket Setup (30 sec)

1. Admin → Buckets → Click "+"
2. **Bucket Name:** `quilt-smoke-test-bucket` (or your test bucket)
3. **Title:** `Smoke Test Bucket`
4. Click "Add"
5. Click Q logo (upper right) → Select the new bucket
6. ✅ **Success:** Overview page loads, tabs are clickable

#### 3. Quick Package Creation (2 min)

1. Packages tab → "Create New Package"
2. **Quick test files:** Create these simple files locally:
   ```
   test.txt: "This is a smoke test file"
   data.csv: "name,value\ntest,123"
   ```
3. Drag files into Quilt or "Add Local Files"
4. **Commit message:** `Smoke test package`
5. **Metadata:**
   - Key: `test_type` Value: `smoke_test`
   - Key: `author` Value: `your-name`
6. Click "Create"
7. ✅ **Success:** Package created, preview shows files

#### 4. Search Validation (1 min)

1. Search button (top bar) → Enter `smoke_test`
2. ✅ **Success:** Your package appears in results
3. Click package → Verify files are visible and readable

> **Combined test:** This validates package creation, indexing, search, and preview in one step.

#### 5. Query Test (30 sec)

1. Queries tab → Enter and run:
   ```sql
   SHOW TABLES
   ```
2. Look for `your-bucket-name_packages-view`
3. **Quick metadata query:**
   ```sql
   SELECT *
   FROM "your-bucket-name_packages-view"
   WHERE json_extract_scalar(user_meta, '$.test_type') = 'smoke_test'
   LIMIT 5
   ```
4. ✅ **Success:** Query returns your test package

---

## 🎉 Smoke Test Complete!

**Total time:** ~5 minutes  
**Validated:** Login, bucket access, package creation, search, and queries

### Next Steps
- For comprehensive testing, run detailed validation scripts
- Monitor logs for any warnings during testing
- Test additional file types and workflows as needed
