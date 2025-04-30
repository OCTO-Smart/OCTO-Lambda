import os
import boto3
import psycopg2
import json
from psycopg2 import sql
from botocore.exceptions import ClientError
from datetime import datetime

USER_POOL_ID = os.getenv("COGNITOPOOLID")
CLIENT_ID    = os.getenv("COGNITOCLIENTID")
REGION       = os.getenv("REGION")

#cognito = boto3.client(CLIENT_ID, region_name=REGION)
cognito = boto3.client("cognito-idp", region_name=REGION)


DB_PARAMS = {
    'host':     os.getenv('DBHOST'),
    'dbname':   os.getenv('DBNAME'),
    'user':     os.getenv('DBUSER'),
    'password': os.getenv('DBPASSWORD'),
    'port':     os.getenv('DBPORT', '5432')
}


# def validate_db_params():
#     missing = [k for k, v in DB_PARAMS.items() if not v]
#     if missing:
#         print(f"Error: Missing DB params: {missing}")
#         return False
#     return True


def lambda_handler(event, context):
    print("Raw event body:", event.get("body"))
    try:
        conn = psycopg2.connect(**DB_PARAMS)

        if "body" in event and isinstance(event["body"], str):
            data = json.loads(event["body"])
        elif "body" in event and isinstance(event["body"], dict):
            data = event["body"]
        else:
            data = event

        
        email     = data.get('email')
        name      = data.get('name')
        lastname  = data.get('lastname')
        password  = data.get('password')

        # Step 1: Signup to Cognito
        signup_response = cognito.sign_up(
            ClientId=CLIENT_ID,
            Username=email,
            Password=password,
            UserAttributes=[
                {'Name': 'email', 'Value': email},
                {'Name': 'given_name', 'Value': name},
                {'Name': 'family_name', 'Value': lastname}
            ]
        )

        # Step 2: Auto-confirm the user
        cognito.admin_confirm_sign_up(
            UserPoolId=USER_POOL_ID,
            Username=email
        )

        user_sub = signup_response['UserSub']
        created_at = datetime.utcnow()

        with conn.cursor() as cur:
            query = sql.SQL(
                "INSERT INTO {table} (cognito_sub, name, lastname, email, created_at) "
                "VALUES (%s, %s, %s, %s, %s)"
            ).format(
                table=sql.Identifier("user")
            )
            cur.execute(query, (user_sub, name, lastname, email, created_at))
            conn.commit()
            print(f"User inserted: {email}")

        return {
            "statusCode": 200,
            "body": json.dumps({"message": f"User {email} created successfully"})
        }

    except Exception as e:
        print(f"Error during signup or DB insert: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

    finally:
        if 'conn' in locals():
            conn.close()
