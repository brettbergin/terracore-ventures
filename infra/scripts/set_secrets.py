import boto3
import getpass

secrets = [
    ("terracore/FLASK_SECRET_KEY", "Flask secret key"),
    ("terracore/MYSQL_USER", "MySQL user"),
    ("terracore/MYSQL_PASSWORD", "MySQL password"),
    ("terracore/GOOGLE_OAUTH_CLIENT_ID", "Google OAuth client ID"),
    ("terracore/GOOGLE_OAUTH_CLIENT_SECRET", "Google OAuth client secret"),
    ("terracore/OPENAI_API_KEY", "OpenAI API key"),
]

client = boto3.client('secretsmanager')

for name, desc in secrets:
    value = getpass.getpass(f"Enter value for {desc} ({name}): ")
    try:
        # Try to put a new version, or create if not exists
        client.put_secret_value(SecretId=name, SecretString=value)
        print(f"Updated {name}")
    except client.exceptions.ResourceNotFoundException:
        client.create_secret(Name=name, SecretString=value)
        print(f"Created {name}") 