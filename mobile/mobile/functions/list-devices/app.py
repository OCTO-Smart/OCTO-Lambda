import os
import json
import logging
import psycopg2
from psycopg2 import sql

# ——— Logging Ayarları ———
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ——— DB Parametreleri (env’den) ———
DB_PARAMS = {
    'host':     os.getenv("DB_HOST"),
    'dbname':   os.getenv("DB_NAME"),
    'user':     os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD"),
    'port':     os.getenv("DB_PORT", "5432"),
    'sslmode':  os.getenv("DB_SSLMODE", "require")
}

def get_db_connection():
    return psycopg2.connect(**DB_PARAMS)

def lambda_handler(event, context):
    try:
        logger.info("Received event: %s", json.dumps(event))

        # 1) Cognito sub’ı al
        claims      = event["requestContext"]["authorizer"]["jwt"]["claims"]
        cognito_sub = claims["sub"]
        logger.info("Cognito sub from token: %s", cognito_sub)

        # 2) sub’a karşılık internal user_id’yi bulun
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL('SELECT id FROM "user" WHERE cognito_sub = %s'),
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

                # 3) Cihaz listesini sorgula
                cur.execute(
                    """
                    SELECT
                      ud.device_id,
                      EXTRACT(EPOCH FROM ud.updated_at)::BIGINT AS updated_at,
                      ds.status
                    FROM user_devices ud
                    LEFT JOIN device_status ds ON ud.device_id = ds.device_id
                    WHERE ud.user_id = %s
                    """,
                    (internal_user_id,)
                )
                devices = []
                for device_id, updated_at, status in cur.fetchall():
                    # status sütunu JSON ya da NULL olabilir
                    device = {
                        "deviceid":   device_id,
                        "updated_at": int(updated_at),
                        "status":     status if isinstance(status, dict)
                                      else (json.loads(status) if status else {})
                    }
                    devices.append(device)
        finally:
            conn.close()

        # 4) Başarılı cevap
        return {
            "statusCode": 200,
            "body": json.dumps({"devices": devices}),
            "headers": {"Content-Type": "application/json"}
        }

    except Exception as e:
        logger.error("Error in ListDevices Lambda Function: %s", str(e), exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Content-Type": "application/json"}
        }
