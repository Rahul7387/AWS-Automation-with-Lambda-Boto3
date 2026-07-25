import boto3
import os
from datetime import datetime, timezone, timedelta

VOLUME_ID = os.environ.get("VOLUME_ID", "vol-0b28c036a11912ffc")
RETENTION_DAYS = int(os.environ.get("RETENTION_DAYS", "30"))
TAG_KEY = "CreatedBy"
TAG_VALUE = "Lambda-Backup"

def lambda_handler(event, context):
    ec2 = boto3.client("ec2")
    now = datetime.now(timezone.utc)
    retention_threshold = now - timedelta(days=RETENTION_DAYS)

    # Step 1: Create a new snapshot
    print(f"Creating snapshot for volume: {VOLUME_ID}")
    snapshot = ec2.create_snapshot(
        VolumeId=VOLUME_ID,
        Description=f"Automated backup of {VOLUME_ID} on {now.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        TagSpecifications=[
            {
                "ResourceType": "snapshot",
                "Tags": [
                    {"Key": TAG_KEY, "Value": TAG_VALUE},
                    {"Key": "VolumeId", "Value": VOLUME_ID},
                    {"Key": "CreatedDate", "Value": now.strftime("%Y-%m-%d")},
                ],
            }
        ],
    )
    new_snapshot_id = snapshot["SnapshotId"]
    print(f"CREATED snapshot: {new_snapshot_id}")

    # Step 2: Find and delete old snapshots
    deleted_snapshots = []

    response = ec2.describe_snapshots(
        OwnerIds=["self"],
        Filters=[
            {"Name": f"tag:{TAG_KEY}", "Values": [TAG_VALUE]},
            {"Name": "tag:VolumeId", "Values": [VOLUME_ID]},
        ],
    )

    for snap in response["Snapshots"]:
        snap_id = snap["SnapshotId"]
        start_time = snap["StartTime"]

        if start_time < retention_threshold:
            try:
                ec2.delete_snapshot(SnapshotId=snap_id)
                deleted_snapshots.append(snap_id)
                print(f"DELETED old snapshot: {snap_id} (StartTime: {start_time})")
            except Exception as e:
                print(f"ERROR deleting snapshot {snap_id}: {e}")
        else:
            print(f"RETAINED snapshot: {snap_id} (StartTime: {start_time})")

    print(f"\n=== SUMMARY ===")
    print(f"Volume: {VOLUME_ID}")
    print(f"New Snapshot: {new_snapshot_id}")
    print(f"Deleted: {len(deleted_snapshots)} old snapshots")

    return {
        "volume_id": VOLUME_ID,
        "new_snapshot_id": new_snapshot_id,
        "deleted_count": len(deleted_snapshots),
        "deleted_snapshots": deleted_snapshots,
    }
