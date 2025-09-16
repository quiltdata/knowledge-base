# Quilt Platform Release 1.63.0

This release dramatically streamlines the ability to manage and package files in S3 buckets, and fixes several UI issues.

## New Features

- **File Upload to S3 Buckets**
  You can now upload files directly to S3 buckets through the Quilt interface.

- **File Deletion from S3 Buckets**
  Delete one or more files from S3 buckets without needing to use the AWS Console or CLI. Note that this only adds a delete marker to the latest version, so prior versions will still be available from packages.

- **Reorganized Bucket Page Toolbar**
  The bucket page toolbar has been reorganized to better manage selections and support the new actions.

- **Streamlined Package Creation**
  Users can now create packages directly from files in the current bucket by default, with S3 file selection always enabled for the current bucket. Administrators can still choose to create a configuration file that disables this.

- **Improved Add Bucket Navigation**
  The "Add Bucket" buttons on the main page now route directly to the Add Bucket admin page for a more intuitive workflow.

## Bug Fixes

- Fixed an issue where the Athena query body would flicker during execution loading.
- Fixed the sign-in button to correctly display the username after successful authentication.
