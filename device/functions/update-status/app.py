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
ADD_DEVICE_FUNCTION_NAME = os.environ.get("ADD_DEVICE_FUNCTION_NAME")

s3 = boto3.client("s3", region_name=REGION)
lambda_client = boto3.client("lambda", region_name=REGION)

def lambda_handler(event, context):
    logger.info("Lambda started.")
    try:
        logger.info("Step 1: Incoming event received")
        logger.info(f"Event raw: {json.dumps(event)}")
        data = json.loads(event["body"]) if "body" in event else event
        logger.info("Step 2: JSON parsed successfully")


        serial = data.get("serial")
        status = data.get("status")

        if not serial:
            raise Exception("Serial not found in JSON")
        if not status:
            raise Exception("Status not found in JSON")
        logger.info(f"Step 3: Serial extracted: {serial}")


        file_name = f"{serial}.json"
        logger.info(f"Step 4: S3 file name generated: {file_name}")


        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=file_name,
            Body=json.dumps({"serial": serial, "status": status}),
            ContentType="application/json"
        )
        logger.info("Step 5: Successfully written to S3.")


        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=5432,
            sslmode="require"
        )
        logger.info("Step 6: Database connection established.")


        cur = conn.cursor()
        cur.execute("SELECT id FROM device WHERE serial_number = %s", (serial,))
        row = cur.fetchone()
        device_id = row[0] if row else None
        logger.info(f"Step 7: Device ID lookup result: {device_id}")


        if not device_id:
            logger.info(f"Device '{serial}' not found. Invoking AddDeviceFunction...")

            add_payload = {
                "userid": data.get("userid", 1),
                "devicename": status.get("dn", f"auto-{serial}"),
                "serial": serial,
                "type": data.get("type", 1)
            }
            logger.info(f"AddDeviceFunction payload: {add_payload}")

            response = lambda_client.invoke(
                FunctionName=ADD_DEVICE_FUNCTION_NAME,
                InvocationType='RequestResponse',
                Payload=json.dumps({"body": json.dumps(add_payload)})
            )
            add_response = json.loads(response["Payload"].read())
            logger.info(f"AddDeviceFunction response: {add_response}")


            cur.execute("SELECT id FROM device WHERE serial_number = %s", (serial,))
            row = cur.fetchone()
            device_id = row[0] if row else None
            if not device_id:
                raise Exception(f"Device '{serial}' could not be added via AddDeviceFunction.")

 
        upsert_sql = """
        INSERT INTO device_status (device_id, status, updated_at)
        VALUES (%s, %s, NOW())
        ON CONFLICT (device_id)
        DO UPDATE SET
          status     = EXCLUDED.status,
          updated_at = EXCLUDED.updated_at;
        """
        cur.execute(upsert_sql, (device_id, json.dumps(status)))
        logger.info(f"UPSERT device_status rowcount: {cur.rowcount}")


        cur.execute(
            "INSERT INTO device_log (device_id, status, timestamp) VALUES (%s, %s, NOW())",
            (device_id, json.dumps(status))
        )


        conn.commit()
        cur.close()
        conn.close()
        logger.info("Step 8: Status updated & log inserted successfully.")

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
        logger.error(f"ERROR occurred during Lambda execution: {error}", exc_info=True)
        try:
            cur.close()
            conn.close()
        except:
            pass
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(error)}),
            "headers": {
                "Content-Type": "application/json"
            }
        }
