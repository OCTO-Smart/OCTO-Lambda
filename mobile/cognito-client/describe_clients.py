import boto3

client = boto3.client('cognito-idp', region_name='eu-central-1')

response = client.list_user_pool_clients(
    UserPoolId='eu-central-1_HvFYYtPGY'
)

for app in response['UserPoolClients']:
    print(f"App Name: {app['ClientName']} | ID: {app['ClientId']}")
