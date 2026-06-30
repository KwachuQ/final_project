import boto3
from app.settings import get_settings


def get_s3_client():
    """Return an S3 client configured with the settings from the .env file.
    """
    settings = get_settings()

    client_kwargs = {
        "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
        "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
        "region_name": settings.AWS_REGION,
    }

    if settings.AWS_ENDPOINT_URL:
        client_kwargs["endpoint_url"] = settings.AWS_ENDPOINT_URL
        
    return boto3.client("s3", **client_kwargs)

def upload_file(key: str, data: bytes):
    """Upload a file to S3."""
    s3 = get_s3_client()
    settings = get_settings()

    try:
        s3.create_bucket(
            Bucket=settings.AWS_BUCKET_NAME,
            CreateBucketConfiguration={
                'LocationConstraint': settings.AWS_REGION
            }
        )
    except s3.exceptions.BucketAlreadyOwnedByYou:
        pass

    try:
        s3.put_object(
            Bucket=settings.AWS_BUCKET_NAME,
            Key=key,
            Body=data
        )

    except Exception as e:
        print(f"Error uploading file to S3: {e}")
        raise

def delete_file(key: str):
    """Delete a file from S3."""
    s3 = get_s3_client()
    settings = get_settings()
    try:
        s3.delete_object(Bucket=settings.AWS_BUCKET_NAME, Key=key)
    except Exception as e:
        print(f"Error deleting file from S3: {e}")
        raise