# Quilt Platform Release 1.63.0

This release dramatically streamlines the experience of creating packages from files already in S3 buckets,
and fixes several UI issues.

## New Features

- **Enhanced Bucket Page Toolbar**
  The Bucket page toolbar has been reorganized for improved consistency, now featuring quick actions for uploading files and deleting single or multiple files.

- **Streamlined Package Creation**
  Users can now create packages directly from files in the current bucket by default, with S3 file selection always enabled for the current bucket. Administrators can still choose to create a configuration file that disables this.

- **Improved Add Bucket Navigation**
  The "Add Bucket" buttons on the main page now route directly to the Add Bucket admin page for a more intuitive workflow.

## Bug Fixes

- Fixed an issue where the Athena query body would flicker during execution loading.
- Fixed the sign-in button not updating to display the username after successful authentication.
- Removed unnecessary blocks and buttons from the deleted file page for a cleaner interface.
