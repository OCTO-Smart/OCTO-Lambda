import os
import json
import logging
import psycopg2

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DB_HOST     = os.getenv("DB_HOST")
DB_NAME     = os.getenv("DB_NAME")
DB_USER     = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT     = os.getenv("DBPORT", "5432")
SSL_MODE    = os.getenv("DB_SSLMODE", "require")

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        sslmode=SSL_MODE
    )

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        device_id = body.get("deviceid")

        if not device_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "deviceid is required"}),
                "headers": {"Content-Type": "application/json"}
            }

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE device SET is_active = FALSE WHERE id = %s",
                (device_id,)
            )
            conn.commit()

        return {
            "statusCode": 200,
            "body": json.dumps({"message": f"Device {device_id} marked as inactive"}),
            "headers": {"Content-Type": "application/json"}
        }

    except Exception as e:
        logger.error("Error in DeleteDeviceFunction: %s", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Content-Type": "application/json"}
        }

#Deploy Test 1 1 1 