import os
import boto3
import psycopg2
from psycopg2 import sql
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
dotenv_path = os.getenv('DOTENV_PATH', '.env')
load_dotenv(dotenv_path=dotenv_path)

# Cognito configuration
USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
CLIENT_ID    = os.getenv("COGNITO_APP_CLIENT_ID")
REGION       = os.getenv("AWS_REGION")

# Database connection parameters
DB_PARAMS = {
    'host':     os.getenv('DB_HOST'),
    'dbname':   os.getenv('DB_NAME'),
    'user':     os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'port':     os.getenv('DB_PORT', '5432')
}

# Application-specific settings: user id to update in DB
USER_TABLE       = os.getenv("USER_TABLE", "user")
USER_PK_COLUMN   = os.getenv("USER_PK_COLUMN", "id")
USER_ID          = os.getenv("USER_ID")  # must be set to target user id
COGNITO_SUB_COL  = os.getenv("USER_COGNITO_COLUMN", "cognito_sub")

# Initialize Cognito client
cognito = boto3.client("cognito-idp", region_name=REGION)


def validate_db_params():
    missing = [k for k, v in DB_PARAMS.items() if not v]
    if missing:
        print(f"Error: Missing DB params: {missing}")
        return False
    if not USER_ID:
        print("Error: USER_ID environment variable not set.")
        return False
    return True


def get_cognito_sub(email: str) -> str:
    try:
        resp = cognito.admin_get_user(
            UserPoolId=USER_POOL_ID,
            Username=email
        )
        for attr in resp.get('UserAttributes', []):
            if attr['Name'] == 'sub':
                return attr['Value']
    except ClientError as e:
        print(f"Error fetching user {email}: {e.response['Error']['Message']}")
    return None


def update_db_sub_by_user_id(user_sub: str):
    if not validate_db_params():
        return
    try:
        conn = psycopg2.connect(**DB_PARAMS)
    except Exception as e:
        print(f"DB connection failed: {e}")
        return

    try:
        with conn.cursor() as cur:
            # Update only the cognito_sub field for known user ID
            query = sql.SQL(
                "UPDATE {table} SET {cog_col} = %s WHERE {pk_col} = %s;"
            ).format(
                table=sql.Identifier(USER_TABLE),
                cog_col=sql.Identifier(COGNITO_SUB_COL),
                pk_col=sql.Identifier(USER_PK_COLUMN)
            )
            cur.execute(query, (user_sub, USER_ID))
            if cur.rowcount == 0:
                print(f"No rows updated: user ID {USER_ID} not found in table {USER_TABLE}.")
            else:
                print(f"Cognito sub updated for user ID {USER_ID}.")
            conn.commit()
    except Exception as e:
        print(f"Error during DB update: {e}")
    finally:
        conn.close()


def signup(password: str, email: str):
    user_sub = None
    try:
        resp = cognito.sign_up(
            ClientId=CLIENT_ID,
            Username=email,
            Password=password,
            UserAttributes=[{'Name': 'email', 'Value': email}]
        )
        user_sub = resp.get('UserSub')
        print(f"Sign-up successful, sub={user_sub}")
    except ClientError as e:
        code = e.response['Error']['Code']
        if code == 'UsernameExistsException':
            print("User exists, fetching sub...")
            user_sub = get_cognito_sub(email)
        else:
            print(f"Sign-up error: {e.response['Error']['Message']}")
            return

    if not user_sub:
        print("Could not obtain sub for user")
        return

    # Sync only existing DB record by primary key
    update_db_sub_by_user_id(user_sub)


if __name__ == '__main__':
    # Pass USER_ID via environment or substitute here for testing
    signup(
        password='StrongP@ssword1',
        email='mert@example.com'
    )
