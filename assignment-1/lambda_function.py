import boto3
import os
from datetime import datetime, timezone, timedelta

BUCKET_NAME = os.environ.get("BUCKET_NAME", "my-cleanup-demo-bucket-rahul")
AGE_THRESHOLD_DAYS = int(os.environ.get("AGE_THRESHOLD_DAYS", "30"))

def lambda_handler(event, context):
    s3 = boto3.client("s3")
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(days=AGE_THRESHOLD_DAYS)

    deleted_objects = []
    retained_objects = []

    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=BUCKET_NAME)

    for page in pages:
        contents = page.get("Contents", [])
        for obj in contents:
            key = obj["Key"]
            last_modified = obj["LastModified"]

            if last_modified < threshold:
                s3.delete_object(Bucket=BUCKET_NAME, Key=key)
                deleted_objects.append(key)
                print(f"DELETED: {key} (LastModified: {last_modified})")
            else:
                retained_objects.append(key)
                print(f"RETAINED: {key} (LastModified: {last_modified})")

    print(f"\n=== SUMMARY ===")
    print(f"Bucket: {BUCKET_NAME}")
    print(f"Threshold: {AGE_THRESHOLD_DAYS} days")
    print(f"Deleted: {len(deleted_objects)} objects")
    print(f"Retained: {len(retained_objects)} objects")

    return {
        "bucket": BUCKET_NAME,
        "threshold_days": AGE_THRESHOLD_DAYS,
        "deleted_count": len(deleted_objects),
        "retained_count": len(retained_objects),
        "deleted_objects": deleted_objects,
    }
