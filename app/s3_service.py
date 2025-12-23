import boto3
from botocore.exceptions import ClientError
from botocore.client import Config
from typing import Optional
import hashlib
import mimetypes
from uuid import UUID

from app.config import settings


class S3Service:
    def __init__(self):
        # Build client parameters
        client_params = {
            'service_name': 's3',
            'region_name': settings.AWS_REGION,
            'config': Config(signature_version='s3v4')
        }

        # Only add credentials if provided (otherwise use IAM role)
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            client_params['aws_access_key_id'] = settings.AWS_ACCESS_KEY_ID
            client_params['aws_secret_access_key'] = settings.AWS_SECRET_ACCESS_KEY

        # Add endpoint URL if provided (for MinIO/local development)
        if settings.S3_ENDPOINT_URL:
            client_params['endpoint_url'] = settings.S3_ENDPOINT_URL

        self.s3_client = boto3.client(**client_params)
        self.bucket_name = settings.S3_BUCKET_NAME

    def generate_s3_key(self, document_id: UUID, version_number: int, filename: str) -> str:
        """Generate a unique S3 key for a document version."""
        # Structure: documents/{document_id}/v{version_number}/{filename}
        return f"documents/{document_id}/v{version_number}/{filename}"

    async def upload_file(
        self,
        file_content: bytes,
        s3_key: str,
        content_type: Optional[str] = None
    ) -> dict:
        """Upload a file to S3."""
        try:
            # Calculate checksum
            checksum = hashlib.sha256(file_content).hexdigest()

            # Determine content type
            if not content_type:
                content_type = mimetypes.guess_type(s3_key)[0] or 'application/octet-stream'

            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                Metadata={
                    'checksum': checksum
                }
            )

            return {
                'success': True,
                's3_key': s3_key,
                'checksum': checksum,
                'size': len(file_content)
            }

        except ClientError as e:
            return {
                'success': False,
                'error': str(e)
            }

    async def download_file(self, s3_key: str) -> Optional[bytes]:
        """Download a file from S3."""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return response['Body'].read()

        except ClientError:
            return None

    def generate_presigned_url(
        self,
        s3_key: str,
        expiration: int = None
    ) -> Optional[str]:
        """Generate a presigned URL for downloading a file."""
        try:
            if expiration is None:
                expiration = settings.PRESIGNED_URL_EXPIRY

            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            return url

        except ClientError:
            return None

    async def delete_file(self, s3_key: str) -> bool:
        """Delete a file from S3."""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True

        except ClientError:
            return False

    async def file_exists(self, s3_key: str) -> bool:
        """Check if a file exists in S3."""
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True

        except ClientError:
            return False

    async def get_file_metadata(self, s3_key: str) -> Optional[dict]:
        """Get metadata for a file in S3."""
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return {
                'size': response['ContentLength'],
                'content_type': response.get('ContentType'),
                'last_modified': response['LastModified'],
                'metadata': response.get('Metadata', {})
            }

        except ClientError:
            return None


# Singleton instance
s3_service = S3Service()
