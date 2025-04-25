import boto3
import hmac
import hashlib
import base64

region = "eu-central-1"
client_id = "4sl7t3o2p1d52haaiv8iqu1mc0"
client_secret = "1qaq8qkvgfedgsmi7jtnbkhqq5v0ll1tkgv0upp3mm6cvb9dd1qq"
username = "testuser@example.com"
password = "Test1234!"

def get_secret_hash(username, client_id, client_secret):
    msg = username + client_id
    dig = hmac.new(
        key=bytes(client_secret, 'utf-8'),
        msg=bytes(msg, 'utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(dig).decode()

client = boto3.client('cognito-idp', region_name=region)

response = client.sign_up(
    ClientId=client_id,
    Username=username,
    Password=password,
    SecretHash=get_secret_hash(username, client_id, client_secret),
    UserAttributes=[
        {
            'Name': 'email',
            'Value': username
        }
    ]
)

print("✅ Signup başarılı:", response)
