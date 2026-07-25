# AWS Automation with Lambda & Boto3

A collection of AWS Lambda functions (Python/Boto3) that automate common cloud operations including resource cleanup, backup management, security auditing, and cost monitoring.

## Assignments

| # | Lambda Function | Description |
|---|----------------|-------------|
| 1 | **S3 Bucket Cleanup** | Deletes S3 objects older than a configurable threshold (default: 30 days) |
| 2 | **EBS Snapshot Manager** | Creates automated EBS snapshots and cleans up snapshots older than the retention period. Triggered on a schedule via EventBridge |
| 3 | **EC2 Auto-Tagger** | Automatically tags new EC2 instances (LaunchDate, Environment, Owner) when they enter the `running` state via EventBridge |
| 4 | **Cost Monitor & Alerter** | Queries month-to-date AWS spend via Cost Explorer and sends an SNS alert when spend exceeds a threshold |
| 5 | **Snapshot Restore & Launch** | Finds the latest EBS snapshot for a volume, registers an AMI, and launches a new EC2 instance from it |
| 6 | **S3 Public Access Auditor** | Audits all S3 buckets for public access (Block Public Access, bucket policies, ACLs) and sends an SNS alert for any findings |

## Repository Structure

```
.
├── lambda_trust_policy.json      # IAM trust policy for Lambda execution role
├── assignment-1/
│   ├── lambda_function.py        # S3 old object cleanup
│   └── iam_policy.json
├── assignment-2/
│   ├── lambda_function.py        # EBS snapshot create & rotate
│   ├── iam_policy.json
│   └── eventbridge_rule.json     # Cron schedule (Sundays 2AM UTC)
├── assignment-3/
│   ├── lambda_function.py        # EC2 auto-tagger
│   ├── iam_policy.json
│   └── eventbridge_pattern.json  # EC2 state-change event pattern
├── assignment-4/
│   ├── lambda_function.py        # Cost monitor with SNS alerts
│   └── iam_policy.json
├── assignment-5/
│   ├── lambda_function.py        # Snapshot restore & instance launch
│   └── iam_policy.json
└── assignment-6/
    ├── lambda_function.py        # S3 public access auditor
    └── iam_policy.json
```

## Setup

1. Create an IAM role for Lambda using `lambda_trust_policy.json` as the trust policy.
2. Attach the corresponding `iam_policy.json` from each assignment folder to the role.
3. Deploy each `lambda_function.py` as an AWS Lambda function (Python 3.12+ runtime).
4. Configure environment variables as needed (bucket names, volume IDs, SNS topic ARNs, thresholds).
5. For event-driven functions (assignments 2 & 3), create EventBridge rules using the provided JSON configs.
