import json
import boto3
import psycopg2
import os
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = "eu-central-1"
BUCKET_NAME = "ivocdevices"

DB_HOST = "ivocdev.cxiqcy2uo0c3.eu-central-1.rds.amazonaws.com"
DB_NAME = "ivocdev"
DB_USER = "ivoc"
DB_PASSWORD = "ivocDevDB!"

s3 = boto3.client("s3", region_name=REGION)

def lambda_handler(event, context):
    logger.info("Lambda started.")

    try:
        logger.info(f"Incoming event: {json.dumps(event)}")

        data = json.loads(event["body"]) if "body" in event else event
        logger.info(f"JSON parsed: {data}")

        device_name = data.get("dn")
        if not device_name:
            raise Exception("Device name (dn) not found in JSON")
        logger.info(f"Device name: {device_name}")

        file_name = f"{device_name}-{int(datetime.utcnow().timestamp() * 1000)}.json"
        logger.info(f"Writing to S3: {file_name}")

        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=file_name,
            Body=json.dumps(data),
            ContentType="application/json"
        )
        logger.info("Successfully written to S3.")

        logger.info("Connecting to database...")
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=5432,
            sslmode="require"
        )

        cur = conn.cursor()
        cur.execute("SELECT id FROM device WHERE name = %s", (device_name,))
        row = cur.fetchone()
        device_id = row[0] if row else None
        logger.info(f"Found device_id: {device_id}")

        if not device_id:
            raise Exception(f"Device '{device_name}' not found in devices table")

        cur.execute(
            "UPDATE device_status SET status = %s, updated_at = NOW() WHERE device_id = %s",
            (json.dumps(data), device_id)
        )
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Status has been updated.")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Data was successfully written to S3 and PostgreSQL.",
                "fileName": file_name
            }),
            "headers": {
                "Content-Type": "application/json"
            }
        }

    except Exception as error:
        logger.error(f"ERROR: {error}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(error)}),
            "headers": {
                "Content-Type": "application/json"
            }
        }
