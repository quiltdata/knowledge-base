#!/usr/bin/env python3
"""
Enable EventBridge integration for CloudTrail
"""

import boto3
import json
from datetime import datetime

# Initialize clients
cloudtrail = boto3.client('cloudtrail', region_name='us-east-1')

try:
    # Get current trail configuration
    trail_response = cloudtrail.get_trail(Name='analytics')
    print(f"Current EventBridge status: {trail_response.get('Trail', {}).get('EventBridgeEnabled', False)}")

    # Update trail to enable EventBridge
    print("\nAttempting to enable EventBridge for CloudTrail...")

    # Try using update_trail with EventBridgeEnabled parameter
    response = cloudtrail.update_trail(
        Name='analytics',
        EventBridgeEnabled=True
    )

    print(f"Success! EventBridge enabled: {response.get('EventBridgeEnabled', False)}")

except Exception as e:
    print(f"Error: {e}")
    print("\nNOTE: EventBridge integration might need to be enabled via AWS Console")
    print("Go to CloudTrail > analytics trail > Edit > Event delivery > Amazon EventBridge")