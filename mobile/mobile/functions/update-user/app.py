import os
import json
import psycopg2
import logging
from datetime import datetime
from psycopg2 import sql

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DB_PARAMS = {
    'host':     os.getenv('DBHOST'),
    'dbname':   os.getenv('DBNAME'),
    'user':     os.getenv('DBUSER'),
    'password': os.getenv('DBPASSWORD'),
    'port':     os.getenv('DBPORT', '5432')
}

ALLOWED_FIELDS = ['name', 'lastname', 'email', 'device_name']

def get_db_connection():
    return psycopg2.connect(**DB_PARAMS)

def lambda_handler(event, context):
    try:
        logger.info("Received event: %s", json.dumps(event))
        claims = event["requestContext"]["authorizer"]["jwt"]["claims"]
        cognito_sub = claims["sub"]

        body = json.loads(event.get("body", "{}"))
        fields_to_update = {k: v for k, v in body.items() if k in ALLOWED_FIELDS and v is not None}

        if not fields_to_update:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "No valid fields to update"}),
                "headers": {"Content-Type": "application/json"}
            }

        # Add updated_at field
        fields_to_update['updated_at'] = datetime.utcnow()

        # Build dynamic SET clause
        set_clauses = [sql.SQL("{} = %s").format(sql.Identifier(k)) for k in fields_to_update]
        values = list(fields_to_update.values())

        update_query = sql.SQL("UPDATE {} SET {} WHERE {} = %s").format(
            sql.Identifier("user"),
            sql.SQL(", ").join(set_clauses),
            sql.Identifier("cognito_sub")
        )
        values.append(cognito_sub)

        conn = get_db_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute(update_query, values)
                if cur.rowcount == 0:
                    return {
                        "statusCode": 404,
                        "body": json.dumps({"message": "User not found"})
                    }

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "User profile updated successfully"})
        }

    except Exception as e:
        logger.error("UpdateUserProfile error: %s", str(e), exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Content-Type": "application/json"}
        }
