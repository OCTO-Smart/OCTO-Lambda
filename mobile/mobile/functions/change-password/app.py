import os
import json
import boto3
from botocore.exceptions import ClientError

REGION = os.getenv("REGION")
cognito = boto3.client("cognito-idp", region_name=REGION)

def lambda_handler(event, context):
    print(json.dumps(event))

    try:

        token = event["headers"].get("authorization", "").replace("Bearer ", "")
        if not token:
            return {
                "statusCode": 401,
                "body": json.dumps({"message": "Missing or invalid token."})
            }

        body = json.loads(event.get("body", "{}"))
        old_password = body.get("old_password")
        new_password = body.get("new_password")

        if not old_password or not new_password:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Both old_password and new_password are required."})
            }

 
        cognito.change_password(
            AccessToken=token,
            PreviousPassword=old_password,
            ProposedPassword=new_password
        )

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Password changed successfully."})
        }

    except ClientError as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": e.response["Error"]["Message"]})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
#Deploy Test
#Deploy