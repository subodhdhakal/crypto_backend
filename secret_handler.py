import json
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
        Retrieve secret with flexible environment and GCP Secret Manager support
        """
        # Check if secret is already in environment
        if os.getenv(secret_name):
            log.info(f"Secret {secret_name} is already set in the environment.")
            return

        # Environment-based routing
        if os.getenv("ENVIRONMENT") == "LOCAL":
            self._set_local_secret(secret_name)
        else:
            self._set_gcp_secret(secret_name)

    def _set_local_secret(self, secret_name):
        """Handle local environment secret retrieval"""
        secret_payload = os.getenv(secret_name)
        if secret_payload:
            os.environ[secret_name] = secret_payload
            log.info(f"Retrieved {secret_name} from local environment")
        else:
            log.error(f"Secret {secret_name} not found in local .env")

    def _set_gcp_secret(self, secret_name):
        """
        Retrieve a specific secret from a single GCP Secret Manager secret bucket
        using JSON format
        """
        try:
            client = secretmanager.SecretManagerServiceClient()
            
            # Use the single secret bucket name
            secret_path = f"projects/{self.gcp_project_id}/secrets/{self.secret_name}/versions/latest"
            
            # Retrieve the entire secret payload
            response = client.access_secret_version(request={"name": secret_path})
            secret_payload = response.payload.data.decode("UTF-8")
            
            try:
                # Parse the JSON payload
                secrets_dict = json.loads(secret_payload)
                
                # Check and set the specific requested secret
                if secret_name in secrets_dict:
                    os.environ[secret_name] = secrets_dict[secret_name]
                    log.info(f"Successfully retrieved {secret_name} from secret bucket")
                else:
                    log.error(f"Secret {secret_name} not found in secret bucket")
                    raise ValueError(f"Secret {secret_name} not found in secret configuration")
            
            except json.JSONDecodeError as json_error:
                log.error(f"Failed to parse secret payload as JSON: {json_error}")
                raise ValueError(f"Invalid JSON format for secrets: {json_error}")
        
        except Exception as e:
            log.error(f"GCP Secret Manager retrieval failed: {str(e)}")
            raise

    # Optional: Add a method to retrieve all secrets if needed
    def get_all_secrets(self):
        """
        Retrieve all secrets from the secret bucket
        """
        try:
            client = secretmanager.SecretManagerServiceClient()
            
            secret_path = f"projects/{self.gcp_project_id}/secrets/{self.secret_name}/versions/latest"
            
            response = client.access_secret_version(request={"name": secret_path})
            secret_payload = response.payload.data.decode("UTF-8")
            
            secrets_dict = json.loads(secret_payload)
            
            # Set all secrets in environment
            for key, value in secrets_dict.items():
                os.environ[key] = value
            
            self.log.info("Successfully retrieved all secrets")
            return secrets_dict
        
        except Exception as e:
            self.log.error(f"Failed to retrieve all secrets: {str(e)}")
            raise
