import os
from google.cloud import secretmanager
from dotenv import load_dotenv
from custom_logger import log

class SecretHandler:
    def __init__(self):
        self.gcp_project_id = 'crypto-volume-change-tracker'
        self.secret_name = 'crypto_secret_bucket'
        
        # Load environment variables from .env if present
        load_dotenv()

    def set_secret(self, secret_name):
        """
        Check if the secret is already set locally; otherwise fetch from GCP.
        """
        if secret_name in os.environ:
            log.info(f"Secret {secret_name} is already set in the environment.")
        else:
            self.set_secret_from_gcp(secret_name)

    def set_secret_from_gcp(self, secret_name):
        """
        Fetch a secret from GCP Secret Manager and set it as an environment variable.
        """
        try:
            # Create the Secret Manager client
            client = secretmanager.SecretManagerServiceClient()

            # Get the secret version
            name = f"projects/{self.gcp_project_id}/secrets/{self.secret_name}/versions/latest"
            
            # Access the secret
            response = client.access_secret_version(name=name)
            
            # Extract the secret payload
            secret_payload = response.payload.data.decode("UTF-8")

            # Set the secret as an environment variable
            os.environ[secret_name] = secret_payload

            log.info(f"Successfully set secret for {secret_name}")
        except Exception as e:
            log.error(f"Failed to fetch secret for {secret_name}: {str(e)}")
