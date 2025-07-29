# Title

"How-To: Validate my new/updated Quilt Catalog is correctly configured"

## Tags

`quilt`, `catalog`, `validation`, `install`, `stack`, `ui`, `s3`

## Summary

End-to-end validation checklist for a new Quilt Catalog stack installation, focusing on core UI functionality, metadata tagging, versioning, preview, access, and sharing.

---

## When to Use This

- Just installed a new Quilt stack, and want to ensure everything works
- Modified your stack or network/security configurations, and want to verify nothing broke
- Users report interimittent errors, and want to identify potential root causes

## Recommendation

Follow this manual validation script to confirm proper operation of Quilt Catalog after stack installation.

---

### Step-by-Step Stack Validation Flow (Editor Role)

1. **Login and Access**

Requires Admin Permissions.

    - Go to your Quilt URL (either directly or, e.g., via an Okta tile).
    - Log in using SSO or IAM user credentials.
    - Go to the upper right corner and click on your user id.
    - Select Admin -> Users and Roles -> Users.
    - Use "+" to add a user.
    - Verify they received and can use that email to login.

> If they don't receive an email, or it has the wrong URL, contact mailto:support@quilt.bio to update the licensing server (which sends those emails).

1. **Adding Buckets**

Requires an existing S3 bucket in the same account (and ideally region), preferably with data.

    - Go to Admin -> Buckets.
    - Click +
    - Enter the Name (not URI) of that bucket, along with a short Title.
    - Click Add
    - Go the bucket picker (upper right Q logo)
    - Select the new bucket
    - Verify it shows the Overview package
    - Click through the top-level tabs

> If the Packages tab is empty, even though there are packages in the bucket, it could be because the index is still being created. This may takes tens of minutes if there are many package revisions.

1. **Upload and Annotate**

Requires a handful of files in different formats, such as those from the [open stack](https://open.quiltdata.com).
Use the "Get Package -> Download Zip" to get all the files separately (instead of via QuiltSync).

    - Go to the Packages tab
    - Click "Create New Package"
    - Drag in those files (or click "Add Local Files")
    - Add a commit message "First"
    - Under "Metadata", add:
        - Key: author
        - Value: <Your Name>
    - Click "Create"

> Creation may fail if your bucket requires a workflow, or the user or bucket lacks write permissions.

1. **Revise a Package**

    - Browse the package
    - Click "Configure Summary" at the bottom
    - Add a couple files
    - Click Save
    - Add a commmit message and "Push" the new revision
    - Verify the additional files show up in the home page preview
    - Click on the hash or "v" to see prior versions

> If some file types do not previews, see the [related Kbase Article](https://kb.quilt.bio/why-are-previews-not-rendering-for-certain-file-types-e.g.-.txt-.png-in-quilt).

1. **Search and Discover**

    - Click on the "Search" button on the top bar
    - Verify it shows a list of existing packages
    - Enter "Your Name" in the Search box, and hit return
    - Verify it shows up in the search Results
    - Explore different filters and modes to see what else is present

> If it does not show up after a while, you may need to [repair the bucket index](https://kb.quilt.bio/fixing-data-display-issues-in-quilt-platform).

1. **Metadata Queries**
    - Go to the Queries tab.
    - Type "Show tables" in the Query body and click "Run Query"
    - Look for the name of `your-bucket`
    - Enter the following query to find your package:

    SELECT *
    FROM "your-bucket_packages-view"
    WHERE json_extract_scalar(user_meta, '$.author') = 'Your Name'

> If you cannot query anything, check your workgroup configuration.
