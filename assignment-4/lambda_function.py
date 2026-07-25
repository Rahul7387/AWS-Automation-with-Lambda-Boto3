import boto3
import os
from datetime import datetime, timezone, timedelta

SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:368763426154:CostAlerts")
COST_THRESHOLD = float(os.environ.get("COST_THRESHOLD", "50.00"))

def lambda_handler(event, context):
    ce = boto3.client("ce")
    sns = boto3.client("sns")

    now = datetime.now(timezone.utc)

    # Query month-to-date cost
    start_date = now.strftime("%Y-%m-01")
    end_date = now.strftime("%Y-%m-%d")

    # If today is the 1st, API requires start < end
    if start_date == end_date:
        yesterday = now - timedelta(days=1)
        start_date = yesterday.strftime("%Y-%m-01")
        end_date = yesterday.strftime("%Y-%m-%d")

    print(f"Querying costs from {start_date} to {end_date}")

    response = ce.get_cost_and_usage(
        TimePeriod={
            "Start": start_date,
            "End": end_date,
        },
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
    )

    # Parse the cost
    results = response["ResultsByTime"]
    total_cost = 0.0
    unit = "USD"

    for result in results:
        amount = float(result["Total"]["UnblendedCost"]["Amount"])
        unit = result["Total"]["UnblendedCost"]["Unit"]
        total_cost += amount

    print(f"Month-to-date spend: ${total_cost:.2f} {unit}")
    print(f"Threshold: ${COST_THRESHOLD:.2f}")

    # Alert if threshold exceeded
    alert_sent = False

    if total_cost > COST_THRESHOLD:
        message = (
            f"AWS Cost Alert\n"
            f"==============================\n"
            f"Month-to-date spend: ${total_cost:.2f}\n"
            f"Threshold: ${COST_THRESHOLD:.2f}\n"
            f"Period: {start_date} to {end_date}\n"
            f"==============================\n"
            f"Please review your AWS usage in Cost Explorer.\n"
        )

        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"AWS Cost Alert: ${total_cost:.2f} exceeds ${COST_THRESHOLD:.2f} threshold",
            Message=message,
        )
        alert_sent = True
        print(f"ALERT SENT to {SNS_TOPIC_ARN}")
    else:
        print("Spend is within threshold. No alert sent.")

    return {
        "total_cost": round(total_cost, 2),
        "threshold": COST_THRESHOLD,
        "alert_sent": alert_sent,
        "period": f"{start_date} to {end_date}",
    }
