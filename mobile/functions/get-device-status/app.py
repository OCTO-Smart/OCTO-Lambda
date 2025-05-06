import os
import json
import logging
import psycopg2
from psycopg2 import sql

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DB_HOST = os.getenv("DBHOST")
DB_NAME = os.getenv("DBNAME")
DB_USER = os.getenv("DBUSER")
DB_PASSWORD = os.getenv("DBPASSWORD")
DB_PORT = os.getenv("DBPORT", "5432")
SSL_MODE = os.getenv("DB_SSLMODE", "require")


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
        logger.info("Received event: %s", json.dumps(event))

        query_params = event.get("queryStringParameters", {}) or {}
        device_id = query_params.get("deviceid")

        if not device_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Missing 'deviceid' query parameter"}),
                "headers": {"Content-Type": "application/json"}
            }

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("SELECT status FROM device_status WHERE device_id = %s"),
                    (device_id,)
                )
                result = cur.fetchone()

                if result is None:
                    return {
                        "statusCode": 404,
                        "body": json.dumps({"message": "Device ID exists but has no status row"}),
                        "headers": {"Content-Type": "application/json"}
                    }

                status_data = result[0]

                if not status_data or (isinstance(status_data, dict) and not status_data):
                    return {
                        "statusCode": 200,
                        "body": json.dumps({"message": "Status is empty", "status": {}}),
                        "headers": {"Content-Type": "application/json"}
                    }

        finally:
            conn.close()

        return {
            "statusCode": 200,
            "body": json.dumps({"status": status_data}),
            "headers": {"Content-Type": "application/json"}
        }

    except Exception as e:
        logger.error("Error in GetDeviceStatus Lambda: %s", str(e), exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error", "detail": str(e)}),
            "headers": {"Content-Type": "application/json"}
        }