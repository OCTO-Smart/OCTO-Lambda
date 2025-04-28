# login.py
import os
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("COGNITO_APP_CLIENT_ID")
REGION    = os.getenv("AWS_REGION")

cognito = boto3.client("cognito-idp", region_name=REGION)

def login(username: str, password: str):
    try:
        resp = cognito.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password
            }
        )
        tokens = resp["AuthenticationResult"]
        print("ID Token:    ", tokens["IdToken"])
        print("Access Token:", tokens["AccessToken"])
        print("Refresh Token:", tokens["RefreshToken"])
    except ClientError as e:
        print("Login error:", e.response["Error"]["Message"])

if __name__ == "__main__":
    login("mert@example.com", "StrongP@ssword1")
