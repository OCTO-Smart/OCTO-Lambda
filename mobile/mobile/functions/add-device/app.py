import os
import json
import logging
import psycopg2
from datetime import datetime


logger = logging.getLogger()
logger.setLevel(logging.INFO)


DB_HOST    = os.getenv("DB_HOST")
DB_NAME    = os.getenv("DB_NAME")
DB_USER    = os.getenv("DB_USER")
DB_PASSWORD= os.getenv("DB_PASSWORD")
DB_PORT    = os.getenv("DB_PORT", "5432")
SSL_MODE   = os.getenv("DB_SSLMODE", "require")

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


        claims     = event["requestContext"]["authorizer"]["jwt"]["claims"]
        cognito_sub= claims["sub"]
        logger.info("Cognito sub from token: %s", cognito_sub)


        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT id FROM "user" WHERE cognito_sub = %s',
                    (cognito_sub,)
                )
                row = cur.fetchone()
                if not row:
                    return {
                        "statusCode": 403,
                        "body": json.dumps({"message": "User not found"}),
                        "headers": {"Content-Type": "application/json"}
                    }
                internal_user_id = row[0]
        finally:
            conn.close()


        body = event.get("body", "{}")
        data = json.loads(body) if isinstance(body, str) else body
        device_name = data.get("devicename")
        serial      = data.get("serial")
        type_       = data.get("type")

        if not all([device_name, serial, type_]):
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Missing device name, serial or type"}),
                "headers": {"Content-Type": "application/json"}
            }

        logger.info(
            "Adding device: serial=%s, name=%s, type=%s for internal_user_id=%s",
            serial, device_name, type_, internal_user_id
        )


        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM device WHERE serial_number = %s",
                    (serial,)
                )
                row = cur.fetchone()

                if row:
                    device_id = row[0]
                    logger.info("Found existing device id=%s", device_id)
                else:
                    created_at = datetime.utcnow()
                    cur.execute("""
                        INSERT INTO device (name, serial_number, type, created_at)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                    """, (device_name, serial, type_, created_at))
                    device_id = cur.fetchone()[0]
                    conn.commit()
                    logger.info("Inserted new device id=%s", device_id)


                cur.execute(
                    "SELECT id FROM user_devices WHERE user_id = %s AND device_id = %s",
                    (internal_user_id, device_id)
                )
                row = cur.fetchone()

                if row:
                    mapping_id = row[0]
                    updated_at = datetime.utcnow()
                    cur.execute(
                        "UPDATE user_devices SET updated_at = %s WHERE id = %s",
                        (updated_at, mapping_id)
                    )
                    conn.commit()
                    logger.info("Updated existing user-device mapping id=%s", mapping_id)
                else:
                    created_at = datetime.utcnow()
                    cur.execute("""
                        INSERT INTO user_devices (user_id, device_id, created_at, updated_at)
                        VALUES (%s, %s, %s, %s)
                    """, (internal_user_id, device_id, created_at, created_at))
                    conn.commit()
                    logger.info("Inserted new user-device mapping for user_id=%s", internal_user_id)

        finally:
            conn.close()


        return {
            "statusCode": 200,
            "body": json.dumps({"deviceid": device_id}),
            "headers": {"Content-Type": "application/json"}
        }

    except Exception as e:
        logger.error("Error in AddDevice Lambda Function: %s", str(e), exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Content-Type": "application/json"}
        }
