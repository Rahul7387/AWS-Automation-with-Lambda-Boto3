import boto3
import os
from datetime import datetime, timezone

DEFAULT_ENVIRONMENT = os.environ.get("DEFAULT_ENVIRONMENT", "Development")

def lambda_handler(event, context):
    ec2 = boto3.client("ec2")

    # Extract instance ID from EventBridge event
    instance_id = event["detail"]["instance-id"]
    print(f"New instance detected: {instance_id}")

    # Build tags
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    tags = [
        {"Key": "LaunchDate", "Value": current_date},
        {"Key": "Environment", "Value": DEFAULT_ENVIRONMENT},
        {"Key": "AutoTagged", "Value": "true"},
    ]

    # Bonus: Extract launching IAM user from CloudTrail
    owner = _get_launcher_from_cloudtrail(event)
    if owner:
        tags.append({"Key": "Owner", "Value": owner})
        print(f"Owner identified from CloudTrail: {owner}")
    else:
        tags.append({"Key": "Owner", "Value": "Unknown"})
        print("Owner could not be determined from event")

    # Apply tags
    ec2.create_tags(Resources=[instance_id], Tags=tags)

    tag_summary = {t["Key"]: t["Value"] for t in tags}
    print(f"Tags applied to {instance_id}: {tag_summary}")

    return {
        "instance_id": instance_id,
        "tags_applied": tag_summary,
    }


def _get_launcher_from_cloudtrail(event):
    """
    Bonus: Attempt to extract the IAM user/role from the
    CloudTrail userIdentity field if present in the event.
    """
    try:
        user_identity = event.get("detail", {}).get("userIdentity", {})
        if "userName" in user_identity:
            return user_identity["userName"]
        if "arn" in user_identity:
            return user_identity["arn"].split("/")[-1]
        if "principalId" in user_identity:
            return user_identity["principalId"].split(":")[-1]
    except Exception as e:
        print(f"CloudTrail owner extraction failed: {e}")
    return None
