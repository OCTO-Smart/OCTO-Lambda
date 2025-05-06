# functions/forgot-password/app.py

import os
import boto3
import json

cognito = boto3.client("cognito-idp", region_name=os.environ["REGION"])
CLIENT_ID = os.environ["COGNITOCLIENTID"]

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        email = body.get("email")

        if not email:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Email is required"}),
                "headers": {"Content-Type": "application/json"}
            }

        response = cognito.forgot_password(
            ClientId=CLIENT_ID,
            Username=email
        )

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Password reset code sent via email."}),
            "headers": {"Content-Type": "application/json"}
        }

    except cognito.exceptions.UserNotFoundException:
        return {
            "statusCode": 404,
            "body": json.dumps({"message": "User not found"}),
            "headers": {"Content-Type": "application/json"}
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Content-Type": "application/json"}
        }
