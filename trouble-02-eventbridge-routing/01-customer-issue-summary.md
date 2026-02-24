# Customer Issue Summary

## Context
**Customer**: FL109 (Flagship Pioneering)
**Date**: December 2024 - December 2025
**Issue**: Packages not appearing in UI after EventBridge setup

## Root Cause
FSx (Amazon FSx for Lustre) overlay on S3 bucket "stole" the S3 event feed, breaking Quilt's package indexing.

## Customer's Attempted Fix
Following the EventBridge documentation at https://docs.quilt.bio/quilt-platform-administrator/advanced/eventbridge, the customer:

1. ✅ Created EventBridge rule: `quilt-s3-events-rule-analytics`
2. ✅ Configured event pattern to capture S3 events (PutObject, CopyObject, CompleteMultipartUpload, DeleteObject, DeleteObjects)
3. ✅ Set bucket filter: `prod-fsp-data-platform-core-analytics`
4. ✅ Set SNS topic as target: `prod-fsp-data-platform-core-analytics-QuiltNotifications-a28a3959-7932-43fd-bfce-1114382382a6`
5. ✅ SNS topic has 3 SQS subscriptions confirmed

## Current Status (Dec 16, 2024)
- **EventBridge rule IS firing** - confirmed by customer
- **Newly added files ARE being indexed**
- **BUT: Package creation events are NOT working**

## The Problem
Customer reports: "Which is the SQS that handles the packaging?"

Looking at the SNS subscriptions screenshot:
- QuiltStack-PackagerQueue has **NO SNS subscriptions** (0)
- Other queues have confirmed SNS subscriptions

This suggests:
1. **File indexing works** (files appear when uploaded)
2. **Package indexing doesn't work** (packages don't appear in UI)
3. **PackagerQueue is not subscribed to the SNS topic**

## Critical Finding
The customer's EventBridge rule is configured with:
- Input to target: **"Matched event"** (no transformation!)

This means events are being sent in **EventBridge/CloudTrail format**, not **S3 notification format**.

## Why This Partially Works
- File events might be processed by a different indexing path
- Package events likely require proper S3 notification format
- Missing input transformer is the likely culprit

## What's Missing from Documentation
1. **Input Transformer configuration** - Customer shows "Matched event" instead of transformed event
2. **PackagerQueue subscription** - Documentation doesn't mention this queue needs SNS subscription
3. **Complete event flow** - Unclear which queues need which subscriptions
4. **Testing guidance** - No way to verify setup is complete before discovering packages don't work

## Next Steps to Fix
1. Add Input Transformer to EventBridge rule target
2. Verify PackagerQueue is subscribed to SNS topic
3. Test package creation end-to-end
4. Update documentation with complete setup including all required queue subscriptions
