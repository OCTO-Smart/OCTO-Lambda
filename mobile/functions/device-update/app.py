import os
import json
import psycopg2
import logging
from psycopg2 import sql

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DB_PARAMS = {
    'host': os.getenv('DBHOST'),
    'dbname': os.getenv('DBNAME'),
    'user': os.getenv('DBUSER'),
    'password': os.getenv('DBPASSWORD'),
    'port': os.getenv('DBPORT', '5432')
}

ALLOWED_FIELDS = ['name', 'serial_number', 'type']

def get_db_connection():
    return psycopg2.connect(**DB_PARAMS)

def lambda_handler(event, context):
    try:
        logger.info("Received event: %s", json.dumps(event))

        body = json.loads(event.get("body", "{}"))
        logger.info("Parsed request body: %s", body)  

        deviceid = body.get("deviceid")
        if not deviceid:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "deviceid is required"})
            }


        fields_to_update = {
            "name": body.get("device_name"),
            "serial_number": body.get("serial"),
            "type": body.get("type")
        }

        fields_to_update = {k: v for k, v in fields_to_update.items() if v is not None}
        logger.info("Fields to update: %s", fields_to_update)

        if not fields_to_update:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "No valid fields to update"})
            }

        set_clauses = [sql.SQL("{} = %s").format(sql.Identifier(k)) for k in fields_to_update]
        values = list(fields_to_update.values())

        update_query = sql.SQL("UPDATE {} SET {} WHERE id = %s").format(
            sql.Identifier("device"),
            sql.SQL(", ").join(set_clauses)
        )
        values.append(deviceid)

        conn = get_db_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute(update_query, values)
                if cur.rowcount == 0:
                    return {
                        "statusCode": 404,
                        "body": json.dumps({"message": "Device not found"})
                    }

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Device updated successfully"})
        }

    except Exception as e:
        logger.error("Device update error: %s", str(e), exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
