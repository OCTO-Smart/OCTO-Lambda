import os
import boto3
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

COGNITO_CLIENT_ID = os.environ.get("COGNITOCLIENTID")
REGION = os.environ.get("REGION")

cognito = boto3.client("cognito-idp", region_name=REGION)

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        email = body.get("email")
        code = body.get("code")
        new_password = body.get("new_password")

        if not all([email, code, new_password]):
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Email, code, and new_password are required"})
            }

        response = cognito.confirm_forgot_password(
            ClientId=COGNITO_CLIENT_ID,
            Username=email,
            ConfirmationCode=code,
            Password=new_password
        )

        logger.info("Cognito confirm_forgot_password response: %s", response)

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Password reset successful"})
        }

    except Exception as e:
        logger.error("Error: %s", str(e), exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
