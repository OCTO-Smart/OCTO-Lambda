# login.py
import os
import boto3
import json
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("COGNITO_APP_CLIENT_ID")
REGION = os.getenv("AWS_REGION")

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
        access_token = tokens["AccessToken"]


        user_info = cognito.get_user(AccessToken=access_token)

        attributes = {attr["Name"]: attr["Value"] for attr in user_info["UserAttributes"]}
        name = attributes.get("name")
        lastname = attributes.get("family_name") or attributes.get("lastname") 


        result = {
            "id_token": tokens["IdToken"],
            "access_token": access_token,
            "refresh_token": tokens["RefreshToken"],
            "name": name,
            "lastname": lastname
        }

        print(json.dumps(result, indent=2))

    except ClientError as e:
        print("Login error:", e.response["Error"]["Message"])

if __name__ == "__main__":
    login("mert@example.com", "StrongP@ssword1")
