import os
import shutil
import boto3
from abc import ABC, abstractmethod
from datetime import datetime

class StorageProvider(ABC):
    @abstractmethod
    def upload_file(self, file_path_or_obj, destination_name: str) -> str:
        """Uploads a file and returns its accessible URL or path."""
        pass

class LocalStorageProvider(StorageProvider):
    def __init__(self, base_dir: str = "resources/antc_data"):
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)
    
    def upload_file(self, file_path_or_obj, destination_name: str) -> str:
        target_path = os.path.join(self.base_dir, destination_name)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        
        if isinstance(file_path_or_obj, str):
            # It's a file path
            shutil.copy2(file_path_or_obj, target_path)
        else:
            # It's a file-like object (bytes)
            with open(target_path, 'wb') as f:
                if hasattr(file_path_or_obj, 'read'):
                    shutil.copyfileobj(file_path_or_obj, f)
                else:
                    f.write(file_path_or_obj)
        
        return f"file://{target_path}"

class S3StorageProvider(StorageProvider):
    def __init__(self):
        self.bucket_name = os.getenv("AWS_S3_BUCKET")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=self.region
        )

    def upload_file(self, file_path_or_obj, destination_name: str) -> str:
        try:
            if isinstance(file_path_or_obj, str):
                self.s3_client.upload_file(file_path_or_obj, self.bucket_name, destination_name)
            else:
                 # Ensure we are at start of stream if it's a file object
                if hasattr(file_path_or_obj, 'seek'):
                    file_path_or_obj.seek(0)
                self.s3_client.upload_fileobj(file_path_or_obj, self.bucket_name, destination_name)
            
            return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{destination_name}"
        except Exception as e:
            print(f"Error uploading to S3: {e}")
            raise e

def get_storage_provider() -> StorageProvider:
    env = os.getenv("ANTC_ENV", "DEV").upper()
    if env == "PROD":
        return S3StorageProvider()
    return LocalStorageProvider()
