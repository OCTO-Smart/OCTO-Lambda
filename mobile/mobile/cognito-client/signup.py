import os
import boto3
import psycopg2
from psycopg2 import sql
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.getenv('DOTENV_PATH', '.env'))

USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
CLIENT_ID    = os.getenv("COGNITO_APP_CLIENT_ID")
REGION       = os.getenv("AWS_REGION")

DB_PARAMS = {
    'host':     os.getenv('DB_HOST'),
    'dbname':   os.getenv('DB_NAME'),
    'user':     os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'port':     os.getenv('DB_PORT', '5432')
}


def validate_db_params():
    missing = [k for k, v in DB_PARAMS.items() if not v]
    if missing:
        print(f"Error: Missing DB params: {missing}")
        return False
    return True


def sign_up(event, context):
    if not validate_db_params():
        return

    try:
        conn = psycopg2.connect(**DB_PARAMS)
    except Exception as e:
        print(f"DB connection failed: {e}")
        return

    try:
        user_attributes = event['request']['userAttributes']
        email     = user_attributes.get('email')
        user_sub  = user_attributes.get('sub')
        name      = user_attributes.get('given_name', '')
        lastname  = user_attributes.get('family_name', '')

        with conn.cursor() as cur:
            query = sql.SQL(
                "INSERT INTO {table} ({sub_col}, {name_col}, {lastname_col}, {email_col}) "
                "VALUES (%s, %s, %s, %s)"
            )
            cur.execute(query, (user_sub, name, lastname, email))
            conn.commit()
            print(f"User inserted: {email}")

    except Exception as e:
        print(f"Error during DB insert: {e}")

    finally:
        conn.close()


