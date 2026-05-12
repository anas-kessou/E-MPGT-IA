"""
MinIO S3-compatible client — document storage with versioning.
"""

import structlog
from minio import Minio
from minio.error import S3Error
from io import BytesIO
from app.config import get_settings

logger = structlog.get_logger()

_client: Minio | None = None


def get_minio_client() -> Minio:
    """Get or create MinIO client singleton."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        logger.info("minio_connected", endpoint=settings.minio_endpoint)
    return _client


def init_bucket():
    """Create the default bucket with versioning if it doesn't exist."""
    client = get_minio_client()
    settings = get_settings()
    bucket = settings.minio_bucket

    try:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            logger.info("minio_bucket_created", bucket=bucket)
        else:
            logger.info("minio_bucket_exists", bucket=bucket)
    except S3Error as e:
        logger.error("minio_bucket_error", error=str(e))


def upload_file(file_data: bytes, object_name: str, content_type: str = "application/pdf") -> str:
    """Upload a file to MinIO. Returns the object path."""
    client = get_minio_client()
    settings = get_settings()

    data_stream = BytesIO(file_data)
    client.put_object(
        settings.minio_bucket,
        object_name,
        data_stream,
        length=len(file_data),
        content_type=content_type,
    )
    logger.info("minio_file_uploaded", object_name=object_name, size=len(file_data))
    return f"{settings.minio_bucket}/{object_name}"


def download_file(object_name: str) -> bytes:
    """Download a file from MinIO."""
    client = get_minio_client()
    settings = get_settings()

    response = client.get_object(settings.minio_bucket, object_name)
    data = response.read()
    response.close()
    response.release_conn()
    return data


def delete_file(object_name: str):
    """Delete a file from MinIO."""
    client = get_minio_client()
    settings = get_settings()
    client.remove_object(settings.minio_bucket, object_name)
    logger.info("minio_file_deleted", object_name=object_name)


def list_files(prefix: str = "") -> list[dict]:
    """List files in the bucket."""
    client = get_minio_client()
    settings = get_settings()

    objects = client.list_objects(settings.minio_bucket, prefix=prefix, recursive=True)
    return [
        {
            "name": obj.object_name,
            "size": obj.size,
            "last_modified": str(obj.last_modified),
            "content_type": obj.content_type,
        }
        for obj in objects
    ]


def health_check() -> str:
    try:
        client = get_minio_client()
        client.list_buckets()
        return "healthy"
    except Exception:
        return "unhealthy"
