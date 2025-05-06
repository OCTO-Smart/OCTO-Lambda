import json
import boto3
import psycopg2
from datetime import datetime
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)


DB_HOST = os.environ.get("DB_HOST")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
REGION = os.environ.get("REGION")
ENV = os.environ.get("ENV")
BUCKET_NAME = "ivocdevices"

print("DEBUG: ENV =", ENV)
print("DEBUG: DB_HOST =", DB_HOST)
print("DEBUG: BUCKET_NAME =", BUCKET_NAME)

logger.info(f"Loaded DB_HOST: {DB_HOST}")
logger.info("Initializing boto3 S3 client...")

s3 = boto3.client("s3", region_name=REGION)
logger.info("S3 client initialized.")


def lambda_handler(event, context):
    logger.info("Lambda started.")
    print(" Lambda logged in!")

    try:
        logger.info("Step 1: Incoming event received")
        logger.info(f"Event raw: {json.dumps(event)}")

        data = json.loads(event["body"]) if "body" in event else event
        logger.info("Step 2: JSON parsed successfully")
        print("JSON Parse done!")

        device_name = data.get("dn")
        if not device_name:
            raise Exception("Device name (dn) not found in JSON")
        logger.info(f"Step 3: Device name extracted: {device_name}")
        print("Device name found:", device_name)

        file_name = f"{device_name}.json"
        logger.info(f"Step 4: S3 file name generated: {file_name}")

        logger.info("Step 5: Attempting to write to S3...")
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=file_name,
            Body=json.dumps(data),
            ContentType="application/json"
        )
        logger.info("Step 6: Successfully written to S3.")
        print("S3 write successful")

        logger.info("Step 7: Attempting to connect to database...")
        print("Trying to connect to database")
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=5432,
            sslmode="require"
        )
        logger.info("Step 8: Database connection established.")
        print("Database connection successful")

        cur = conn.cursor()
        logger.info("Step 9: Executing device ID lookup query...")
        cur.execute("SELECT id FROM device WHERE name = %s", (device_name,))
        row = cur.fetchone()
        device_id = row[0] if row else None
        logger.info(f"Step 10: Found device_id: {device_id}")
        print("Device ID found:", device_id)

        if not device_id:
            #TODO: Cihaz DB'ye kayıtlı değilse, device projesindeki add device ile eklenecek.
            raise Exception(f"Device '{device_name}' not found in devices table")

        logger.info("Step 11: Updating device_status in database...")
        cur.execute(
            "UPDATE device_status SET status = %s, updated_at = NOW() WHERE device_id = %s",
            (json.dumps(data), device_id)
        )

        logger.info("Step 11.5: Inserting log into device_log table...")
        cur.execute(
            "INSERT INTO device_log (device_id, status, timestamp) VALUES (%s, %s, NOW())",
            (device_id, json.dumps(data))
        )
        logger.info("Step 11.6: Log inserted into device_log.")
        print("Log table insert successful")

        conn.commit()
        logger.info("Step 12: Database update committed.")

        cur.close()
        conn.close()
        logger.info("Step 13: Database connection closed.")
        print("Database update completed")

        logger.info("Step 14: Lambda execution completed successfully.")
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
        logger.error(f"ERROR occurred during Lambda execution: {error}")
        print("ERROR:", error)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(error)}),
            "headers": {
                "Content-Type": "application/json"
            }
        }
