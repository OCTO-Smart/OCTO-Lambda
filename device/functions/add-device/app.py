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
SSL_MODE    = os.getenv("DB_SSLMODE")

def lambda_handler(event, context):
    try:
        logging.info("Received event: %s", json.dumps(event))

        body = event.get("body", event)
        data = json.loads(body) if isinstance(body, str) else body

        device_name = data["devicename"]
        serial      = data["serial"]
        device_type       = data["type"]

        logging.info("Attempting to add or lookup device: serial=%s, name=%s, type=%s for user=%s", serial, device_name, device_type )

        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=5432,
            sslmode=SSL_MODE
        )
        cur = conn.cursor()

        cur.execute("SELECT id FROM device WHERE serial_number = %s", (serial,))
        row = cur.fetchone()
        if row:
            device_id = row[0]
            logging.info("Found existing device id=%s for serial=%s", device_id, serial)
        else:
            logging.info("No existing device, inserting new one")
            created_at = datetime.utcnow()
            cur.execute(
                "INSERT INTO device (name, serial_number, type, created_at) VALUES (%s, %s, %s, %s) RETURNING id",
                (device_name, serial, device_type, created_at)
            )
            device_id = cur.fetchone()[0]
            conn.commit()
            logging.info("Inserted new device id=%s", device_id)

        cur.close()
        conn.close()

        response = {
            "statusCode": 200,
            "body": json.dumps({"deviceid": device_id}),
            "headers": {"Content-Type": "application/json"}
        }
        logging.info("Returning response: %s", response)
        return response

    except Exception as e:
        logging.error("Error in AddDeviceFunction: %s", str(e), exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Content-Type": "application/json"}
        }
