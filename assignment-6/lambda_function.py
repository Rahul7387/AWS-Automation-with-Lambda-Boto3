import boto3
import os

SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:368763426154:S3PublicAlerts")

def lambda_handler(event, context):
    s3 = boto3.client("s3")
    sns = boto3.client("sns")

    # Step 1: List all buckets
    response = s3.list_buckets()
    buckets = response.get("Buckets", [])
    print(f"Found {len(buckets)} buckets to audit")

    public_buckets = []

    for bucket in buckets:
        bucket_name = bucket["Name"]
        issues = []

        # Check 1: Block Public Access configuration
        try:
            bpa = s3.get_public_access_block(Bucket=bucket_name)
            config = bpa["PublicAccessBlockConfiguration"]

            if not config.get("BlockPublicAcls", False):
                issues.append("BlockPublicAcls is disabled")
            if not config.get("IgnorePublicAcls", False):
                issues.append("IgnorePublicAcls is disabled")
            if not config.get("BlockPublicPolicy", False):
                issues.append("BlockPublicPolicy is disabled")
            if not config.get("RestrictPublicBuckets", False):
                issues.append("RestrictPublicBuckets is disabled")

        except s3.exceptions.ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchPublicAccessBlockConfiguration":
                issues.append("No Block Public Access configuration set")
            else:
                print(f"  Error checking BPA for {bucket_name}: {e}")

        # Check 2: Bucket Policy Status
        try:
            policy_status = s3.get_bucket_policy_status(Bucket=bucket_name)
            is_public = policy_status["PolicyStatus"]["IsPublic"]
            if is_public:
                issues.append("Bucket policy allows public access")
        except s3.exceptions.ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchBucketPolicy":
                pass
            else:
                print(f"  Error checking policy status for {bucket_name}: {e}")

        # Check 3: ACL Grants
        try:
            acl = s3.get_bucket_acl(Bucket=bucket_name)
            for grant in acl.get("Grants", []):
                grantee = grant.get("Grantee", {})
                uri = grantee.get("URI", "")
                if "AllUsers" in uri:
                    issues.append(f"ACL grants public access (AllUsers): {grant['Permission']}")
                elif "AuthenticatedUsers" in uri:
                    issues.append(f"ACL grants access to all AWS users: {grant['Permission']}")
        except Exception as e:
            print(f"  Error checking ACL for {bucket_name}: {e}")

        # Record results
        if issues:
            public_buckets.append({"bucket": bucket_name, "issues": issues})
            print(f"PUBLIC: {bucket_name}")
            for issue in issues:
                print(f"    - {issue}")
        else:
            print(f"SECURE: {bucket_name}")

    # Step 2: Send SNS alert if any public buckets found
    alert_sent = False

    if public_buckets:
        bucket_details = "\n".join(
            f"  - {b['bucket']}:\n" + "\n".join(f"      - {i}" for i in b["issues"])
            for b in public_buckets
        )

        message = (
            f"S3 Public Access Audit Alert\n"
            f"====================================\n"
            f"Found {len(public_buckets)} bucket(s) with public access:\n\n"
            f"{bucket_details}\n\n"
            f"====================================\n"
            f"Action required: Review and restrict public access.\n"
        )

        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"S3 Audit: {len(public_buckets)} bucket(s) with public access",
            Message=message,
        )
        alert_sent = True
        print(f"\nALERT SENT to {SNS_TOPIC_ARN}")
    else:
        print("\nAll buckets are secure. No alert needed.")

    summary = {
        "total_buckets": len(buckets),
        "public_buckets": len(public_buckets),
        "alert_sent": alert_sent,
        "details": public_buckets,
    }

    print(f"\n=== SUMMARY ===")
    print(f"Total Buckets Audited: {len(buckets)}")
    print(f"Public Buckets Found:  {len(public_buckets)}")
    print(f"Alert Sent:            {alert_sent}")

    return summary
