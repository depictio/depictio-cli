from abc import ABC, abstractmethod
from pydantic import Field
from pydantic_settings import BaseSettings
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError

class MinioConfig(BaseSettings):
    """Minio configuration."""
    internal_endpoint: str = "http://localhost"
    port: int = 9000
    root_user: str = Field(default="minio")
    root_password: str = Field(default="minio123")
    bucket: str = "depictio-bucket"

    class Config:
        env_prefix = 'DEPICTIO_MINIO_'

class S3ProviderBase(ABC):
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name

    @abstractmethod
    def check_s3_accessibility(self):
        pass

    @abstractmethod
    def check_bucket_accessibility(self):
        pass

    @abstractmethod
    def check_write_policy(self):
        pass

    def suggest_adjustments(self):
        suggestions = []
        if not self.check_s3_accessibility():
            suggestions.append("Verify the endpoint URL, access key, and secret key.")
        if not self.check_bucket_accessibility():
            suggestions.append(f"Ensure the bucket '{self.bucket_name}' exists and is accessible.")
        if not self.check_write_policy():
            suggestions.append("Adjust bucket policies to allow write access for this client.")

        if suggestions:
            print("Suggested Adjustments:")
            for suggestion in suggestions:
                print(f"- {suggestion}")
        else:
            print("No adjustments needed.")

class MinIOManager(S3ProviderBase):
    def __init__(self, config: MinioConfig):
        super().__init__(config.bucket)
        self.endpoint_url = f"{config.internal_endpoint}:{config.port}"
        self.access_key = config.root_user
        self.secret_key = config.root_password
        self.s3_client = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key
        )

    def check_s3_accessibility(self):
        try:
            self.s3_client.list_buckets()
            print("S3 is accessible.")
            return True
        except (NoCredentialsError, PartialCredentialsError):
            print("Invalid credentials for S3.")
            return False
        except Exception as e:
            print(f"Error accessing S3: {e}")
            return False

    def check_bucket_accessibility(self):
        try:
            response = self.s3_client.head_bucket(Bucket=self.bucket_name)
            print(f"Bucket '{self.bucket_name}' is accessible.")
            return True
        except ClientError as e:
            print(f"Bucket '{self.bucket_name}' is not accessible: {e.response['Error']['Message']}")
            return False

    def check_write_policy(self):
        try:
            test_key = ".depictio/"
            self.s3_client.put_object(Bucket=self.bucket_name, Key=test_key, Body="test")
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=test_key)
            print("Write policy is correctly configured.")
            return True
        except ClientError as e:
            print(f"Write policy check failed: {e.response['Error']['Message']}")
            return False

if __name__ == "__main__":
    # Load configuration
    config = MinioConfig()

    # Initialize MinIOManager with configuration
    s3_manager = MinIOManager(config)

    # Perform checks and suggest adjustments
    s3_manager.suggest_adjustments()
