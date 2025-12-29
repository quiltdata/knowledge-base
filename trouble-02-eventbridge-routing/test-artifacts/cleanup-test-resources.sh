#!/bin/bash

# Cleanup script for EventBridge routing test resources
# Run this after the test is complete

echo "EventBridge Routing Test - Cleanup Script"
echo "=========================================="

# Variables
RULE_NAME="quilt-staging-eventbridge-test-v2"
SNS_TOPIC_ARN="arn:aws:sns:us-east-1:712023778557:kevin-spg-stage2-QuiltNotifications-6a803e81-3d68-47a4-9ddc-4d14902f745a"
TEST_BUCKET="quilt-eventbridge-test"
TEST_FILE_KEY="test/eventbridge-test-file-v2.txt"
PROFILE="default"
REGION="us-east-1"

echo ""
echo "This script will remove:"
echo "1. EventBridge rule: $RULE_NAME"
echo "2. Test file: s3://$TEST_BUCKET/$TEST_FILE_KEY"
echo "3. Restore original SNS policy (optional)"
echo ""
read -p "Do you want to proceed? (y/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting cleanup..."

    # 1. Remove EventBridge targets first
    echo "Removing EventBridge rule targets..."
    aws events remove-targets \
        --rule "$RULE_NAME" \
        --ids "1" \
        --profile $PROFILE \
        --region $REGION

    # 2. Delete EventBridge rule
    echo "Deleting EventBridge rule..."
    aws events delete-rule \
        --name "$RULE_NAME" \
        --profile $PROFILE \
        --region $REGION

    # 3. Delete test file from S3
    echo "Deleting test file from S3..."
    aws s3 rm "s3://$TEST_BUCKET/$TEST_FILE_KEY" \
        --profile $PROFILE

    # 4. Ask about SNS policy restoration
    echo ""
    read -p "Do you want to restore the original SNS policy? (y/N) " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Find the latest backup file
        BACKUP_FILE=$(ls -t kevin-spg-sns-policy-backup-*.json 2>/dev/null | head -1)

        if [ -f "$BACKUP_FILE" ]; then
            echo "Restoring SNS policy from: $BACKUP_FILE"

            # Extract just the Policy attribute
            POLICY=$(jq -r '.Attributes.Policy' "$BACKUP_FILE")

            # Set the policy
            aws sns set-topic-attributes \
                --topic-arn "$SNS_TOPIC_ARN" \
                --attribute-name Policy \
                --attribute-value "$POLICY" \
                --profile $PROFILE

            echo "SNS policy restored"
        else
            echo "No backup file found. Skipping SNS policy restoration."
        fi
    fi

    echo ""
    echo "Cleanup complete!"
    echo ""
    echo "Resources that were NOT removed (still needed for production):"
    echo "- SNS Topic: kevin-spg-stage2"
    echo "- SQS Queues: quilt-staging queues"
    echo "- S3 Bucket: quilt-eventbridge-test (bucket itself)"
    echo "- CloudTrail: analytics trail"

else
    echo "Cleanup cancelled"
fi