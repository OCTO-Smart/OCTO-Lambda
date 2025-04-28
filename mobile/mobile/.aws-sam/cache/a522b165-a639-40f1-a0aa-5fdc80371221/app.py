import os
import json
import logging
import psycopg2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
SSL_MODE = os.getenv("DB_SSLMODE", "require")

def lambda_handler(event, context):
    try:
        logging.info("Received event: %s", json.dumps(event))

        params = event.get("queryStringParameters", {})
        user_id = params.get("userid")

        if not user_id:
            raise Exception("Missing userid parameter in query string.")

        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            sslmode=SSL_MODE
        )
        cur = conn.cursor()

        cur.execute(
            """
            SELECT device_id, EXTRACT(EPOCH FROM updated_at)::BIGINT
            FROM user_devices
            WHERE user_id = %s
            """,
            (user_id,)
        )
        devices = [{"deviceid": row[0], "updated_at": row[1]} for row in cur.fetchall()]

        cur.close()
        conn.close()

        return {
            "statusCode": 200,
            "body": json.dumps({"devices": devices}),
            "headers": {"Content-Type": "application/json"}
        }

    except Exception as e:
        logging.error("Error in Lambda Function: %s", str(e), exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Content-Type": "application/json"}
        }
