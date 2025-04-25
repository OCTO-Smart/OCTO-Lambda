import os
import json
import logging
import psycopg2
from datetime import datetime 

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

DB_HOST     = os.getenv("DB_HOST")
DB_NAME     = os.getenv("DB_NAME")
DB_USER     = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT     = int(os.getenv("DB_PORT", "5432"))
SSL_MODE    = os.getenv("DB_SSLMODE", "require")

def lambda_handler(event, context):
    try:
        logging.info("Received event: %s", json.dumps(event))

        body = event.get("body", event)
        data = json.loads(body) if isinstance(body, str) else body

        user_id     = data["userid"]
        device_name = data["devicename"]
        serial      = data["serial"]
        type_       = data["type"]

        logging.info(
            "Checking device: serial=%s, name=%s, type=%s for user=%s",
            serial, device_name, type_, user_id
        )

        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            sslmode=SSL_MODE
        )
        cur = conn.cursor()


        cur.execute("SELECT id FROM device WHERE serial_number = %s", (serial,))
        row = cur.fetchone()

        if row:
            device_id = row[0]
            logging.info("Found existing device id=%s", device_id)
        else:

            created_at = datetime.now()

            cur.execute(
                """
                INSERT INTO device (name, serial_number, type, created_at)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (device_name, serial, type_, created_at)
            )
            device_id = cur.fetchone()[0]
            conn.commit()
            logging.info("Inserted new device id=%s", device_id)

        cur.execute(
            "SELECT 1 FROM user_devices WHERE user_id = %s AND device_id = %s",
            (user_id, device_id)
        )
        if not cur.fetchone():
            created_at_mapping = datetime.now()

            cur.execute(
            "INSERT INTO user_devices (user_id, device_id, created_at) VALUES (%s, %s, %s)",
            (user_id, device_id, created_at_mapping)
        )
            conn.commit()
            logging.info("User-device mapping created")

        cur.close()
        conn.close()

        return {
            "statusCode": 200,
            "body": json.dumps({"deviceid": device_id}),
            "headers": {"Content-Type": "application/json"}
        }

    except Exception as e:
        logging.error("Error in AddDeviceFunction: %s", str(e), exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Content-Type": "application/json"}
        }
