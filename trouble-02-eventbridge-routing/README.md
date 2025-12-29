# Trouble Report: EventBridge Routing Documentation

**Date**: 2025-12-29
**Reporter**: Customer
**Issue**: Current EventBridge documentation steps do not work

## Customer Report
Customer claims the current documentation at https://docs.quilt.bio/quilt-platform-administrator/advanced/eventbridge does not work when followed.

## Investigation Plan
1. Review current documentation steps in detail
2. Set up test environment
3. Reproduce each step exactly as documented
4. Identify gaps, errors, or missing information
5. Document corrections needed

## Current Documentation Overview
The docs describe three approaches:
- SNS Fanout (recommended)
- EventBridge Routing
- Just-in-Time Resources

Customer is likely attempting **EventBridge Routing** since that's the main focus of the page.

## Key Areas to Test
- [ ] CloudTrail configuration requirements
- [ ] EventBridge rule creation
- [ ] Input transformer configuration (critical - converts EventBridge to S3 format)
- [ ] SNS topic setup and permissions
- [ ] Quilt configuration changes
- [ ] End-to-end event flow

## Notes

### Potential Issues (to investigate)
- Input transformer syntax may be incorrect or incomplete
- IAM permissions may be missing or incorrect
- Event pattern may not match actual CloudTrail events
- S3 event format conversion may be wrong
- CloudTrail setup steps may be unclear

## Test Environment Setup

TODO: Document test setup here

## Reproduction Steps

TODO: Document exact steps followed

## Findings

TODO: Document what works and what doesn't

## Recommended Fixes

TODO: Document corrections needed for the documentation
