import boto3
import os
from datetime import datetime, timezone

VOLUME_ID = os.environ.get("VOLUME_ID", "vol-0b28c036a11912ffc")
INSTANCE_TYPE = os.environ.get("INSTANCE_TYPE", "t3.micro")
SUBNET_ID = os.environ.get("SUBNET_ID", "")
ARCHITECTURE = os.environ.get("ARCHITECTURE", "x86_64")

def lambda_handler(event, context):
    ec2 = boto3.client("ec2")

    # Step 1: Find the most recent snapshot for the volume
    print(f"Looking for snapshots of volume: {VOLUME_ID}")

    response = ec2.describe_snapshots(
        OwnerIds=["self"],
        Filters=[
            {"Name": "volume-id", "Values": [VOLUME_ID]},
            {"Name": "status", "Values": ["completed"]},
        ],
    )

    snapshots = response["Snapshots"]
    if not snapshots:
        error_msg = f"No completed snapshots found for volume {VOLUME_ID}"
        print(f"ERROR: {error_msg}")
        return {"error": error_msg}

    # Sort by StartTime descending to get the latest
    snapshots.sort(key=lambda s: s["StartTime"], reverse=True)
    latest_snapshot = snapshots[0]
    snapshot_id = latest_snapshot["SnapshotId"]
    print(f"Latest snapshot: {snapshot_id} (StartTime: {latest_snapshot['StartTime']})")

    # Step 2: Register an AMI from the snapshot
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    ami_name = f"restored-from-{snapshot_id}-{timestamp}"

    print(f"Registering AMI: {ami_name}")

    ami_response = ec2.register_image(
        Name=ami_name,
        Description=f"AMI restored from snapshot {snapshot_id} of volume {VOLUME_ID}",
        Architecture=ARCHITECTURE,
        RootDeviceName="/dev/xvda",
        BlockDeviceMappings=[
            {
                "DeviceName": "/dev/xvda",
                "Ebs": {
                    "SnapshotId": snapshot_id,
                    "VolumeType": "gp3",
                    "DeleteOnTermination": True,
                },
            }
        ],
        VirtualizationType="hvm",
        EnaSupport=True,
    )

    ami_id = ami_response["ImageId"]
    print(f"AMI registered: {ami_id}")

    # Step 3: Wait for AMI to become available
    print("Waiting for AMI to become available...")
    waiter = ec2.get_waiter("image_available")
    try:
        waiter.wait(
            ImageIds=[ami_id],
            WaiterConfig={"Delay": 15, "MaxAttempts": 40},
        )
        print(f"AMI {ami_id} is now available")
    except Exception as e:
        print(f"WARNING: Waiter timed out, attempting launch anyway: {e}")

    # Step 4: Launch a new instance from the AMI
    run_params = {
        "ImageId": ami_id,
        "InstanceType": INSTANCE_TYPE,
        "MinCount": 1,
        "MaxCount": 1,
        "TagSpecifications": [
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "Name", "Value": f"Restored-from-{snapshot_id}"},
                    {"Key": "RestoredFrom", "Value": snapshot_id},
                    {"Key": "SourceVolume", "Value": VOLUME_ID},
                    {"Key": "RestoredDate", "Value": timestamp},
                ],
            }
        ],
    }

    if SUBNET_ID:
        run_params["SubnetId"] = SUBNET_ID

    instance_response = ec2.run_instances(**run_params)
    new_instance_id = instance_response["Instances"][0]["InstanceId"]
    print(f"LAUNCHED new instance: {new_instance_id}")

    summary = {
        "source_volume": VOLUME_ID,
        "snapshot_used": snapshot_id,
        "ami_created": ami_id,
        "new_instance_id": new_instance_id,
        "instance_type": INSTANCE_TYPE,
    }

    print(f"\n=== SUMMARY ===")
    print(f"Source Volume: {VOLUME_ID}")
    print(f"Snapshot Used: {snapshot_id}")
    print(f"AMI Created:   {ami_id}")
    print(f"New Instance:  {new_instance_id}")
    print(f"\nRemember to TERMINATE {new_instance_id} after testing!")

    return summary
