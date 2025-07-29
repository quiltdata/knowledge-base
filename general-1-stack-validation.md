# Title

"How do I validate a new Quilt Catalog installation end-to-end?"

## Tags

`quilt`, `catalog`, `validation`, `install`, `stack`, `ui`, `s3`

## Summary

End-to-end validation checklist for a new Quilt Catalog stack installation, focusing on core UI functionality, metadata tagging, versioning, preview, access, and sharing.

---

## Symptoms

- Unclear whether the Quilt Catalog UI and workflows were installed correctly
- Uncertainty around file preview, versioning, metadata tagging, or role-based access
- Inability to verify governance or package sharing behavior

## Likely Causes

- Incomplete or misconfigured stack deployment (e.g. IAM, CloudFormation, S3 policies)
- Insufficient IAM roles or permissions for Quilt Catalog operations
- SSO group/role mapping not correctly wired to user privileges

## Recommendation

Follow this manual validation script to confirm proper operation of Quilt Catalog after stack installation.

---

### Step-by-Step Stack Validation Flow (Editor Role)

1. **Login and Access**
   - Open the Quilt Catalog UI.
   - Log in using SSO or IAM user credentials.
   - Navigate to an assigned bucket or organization root.

2. **Upload and Annotate**
   - Create a new data package via UI.
   - Upload: `experiment.csv`, `plot.png`
   - Add metadata: `sample_id = A12`, `project = CellTracking`, `owner = dr.jane@lab.com`
   - Publish package.

3. **Search and Discover**
   - Use UI search to query:
     - `sample_id:A12`
     - `plot.png`
     - `project:CellTracking`
   - Confirm package is discoverable by metadata and file name.

4. **Preview Files**
   - Open the new package.
   - Validate inline previews:
     - Table view for CSV
     - Image preview for PNG

5. **Version Control**
   - Modify and re-upload a file.
   - Publish a new version.
   - Open version history; confirm rollback is possible.

6. **Secure Sharing**
   - Generate a read-only link.
   - Open in incognito mode.
   - Confirm link access and expiration behavior.

7. **Role-Based Access**
   - Switch to a Viewer account.
   - Confirm:
     - Package is visible
     - Editing is restricted

---

If any of these tests fail, validate IAM roles, CloudFormation output, and catalog configuration.
