import json
import boto3
import psycopg2
from datetime import datetime
import logging
import os
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DB_HOST                     = os.environ["DB_HOST"]
DB_NAME                     = os.environ["DB_NAME"]
DB_USER                     = os.environ["DB_USER"]
DB_PASSWORD                 = os.environ["DB_PASSWORD"]
REGION                      = os.environ["REGION"]
BUCKET_NAME                 = os.environ["BUCKET_NAME"]
ADD_DEVICE_FUNCTION_NAME    = os.environ["ADD_DEVICE_FUNCTION_NAME"]

s3 = boto3.client("s3", region_name=REGION)
lambda_client = boto3.client("lambda", region_name=REGION)

def lambda_handler(event, context):
    logger.info("Lambda started.")
    try:

        raw = event.get("body", event)
        data = json.loads(raw) if isinstance(raw, str) else raw
        logger.info(f"Incoming payload: {data}")


        serial = data.get("serial") or data.get("dn")
        if not serial:
            raise Exception("Serial not found in JSON")
        logger.info(f"Serial: {serial}")

        status = data  


        conn = psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute("SELECT id FROM device WHERE serial_number = %s", (serial,))
        row = cur.fetchone()
        if row:
            device_id = row[0]
            logger.info(f"Existing device_id: {device_id}")
        else:

            payload = {
                "userid":    data.get("userid", 1),
                "devicename": data.get("dn", serial),
                "serial":    serial,
                "type":      data.get("type", 1)
            }
            try:
                resp = lambda_client.invoke(
                    FunctionName=ADD_DEVICE_FUNCTION_NAME,
                    InvocationType='RequestResponse',
                    Payload=json.dumps({"body": json.dumps(payload)})
                )
            except ClientError as e:
                raise Exception(f"Invoke AddDeviceFunction failed: {e}")


            resp_payload = resp["Payload"].read().decode("utf-8")
            add_resp = json.loads(resp_payload)
            body = json.loads(add_resp.get("body", "{}"))
            device_id = body.get("deviceid")
            if not device_id:
                raise Exception("AddDeviceFunction did not return a deviceid")
            logger.info(f"New device_id from AddDeviceFunction: {device_id}")


        timestamp   = datetime.utcnow()
        status_json = json.dumps(status)
        cur.execute("""
            INSERT INTO device_status (device_id, status, updated_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (device_id)
            DO UPDATE SET
              status     = EXCLUDED.status,
              updated_at = EXCLUDED.updated_at
        """, (device_id, status_json, timestamp))
        logger.info("Upserted status record")

        s3_key = f"{serial}/{timestamp.strftime('%Y%m%dT%H%M%SZ')}.json"
        s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=status_json)
        logger.info(f"Wrote to S3: {s3_key}")

        cur.close()
        conn.close()

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Status updated", "deviceid": device_id})
        }

    except Exception as e:
        logger.error(f"ERROR during execution: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
