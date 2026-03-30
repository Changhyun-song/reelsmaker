"""S3-compatible object storage utilities.

Usable from both API (sync boto3) and Worker (sync boto3 in threadpool).
"""

from __future__ import annotations

import uuid

import boto3
from botocore.config import Config

from shared.config import get_settings

_client = None


def _get_client():
    global _client
    if _client is None:
        settings = get_settings()
        _client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=Config(signature_version="s3v4"),
        )
    return _client


def _bucket() -> str:
    return get_settings().s3_bucket


def ensure_bucket() -> None:
    client = _get_client()
    try:
        client.head_bucket(Bucket=_bucket())
    except client.exceptions.ClientError:
        client.create_bucket(Bucket=_bucket())


def generate_storage_key(
    project_id: str | uuid.UUID,
    parent_type: str,
    parent_id: str | uuid.UUID,
    variant_index: int = 0,
    extension: str = "png",
) -> str:
    uid = uuid.uuid4().hex[:8]
    return (
        f"projects/{project_id}/{parent_type}/{parent_id}/"
        f"v{variant_index}_{uid}.{extension}"
    )


def upload_bytes(
    key: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    _get_client().put_object(
        Bucket=_bucket(),
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    return key


def get_presigned_url(key: str, expires_in: int = 3600) -> str:
    url = _get_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": _bucket(), "Key": key},
        ExpiresIn=expires_in,
    )
    settings = get_settings()
    if settings.s3_public_endpoint and settings.s3_endpoint != settings.s3_public_endpoint:
        url = url.replace(settings.s3_endpoint, settings.s3_public_endpoint, 1)
    return url


def download_to_file(key: str, local_path: str) -> str:
    """Download an S3 object to a local file. Returns the local_path."""
    _get_client().download_file(
        Bucket=_bucket(),
        Key=key,
        Filename=local_path,
    )
    return local_path


def upload_file(key: str, local_path: str, content_type: str = "application/octet-stream") -> str:
    """Upload a local file to S3. Returns the key."""
    _get_client().upload_file(
        Filename=local_path,
        Bucket=_bucket(),
        Key=key,
        ExtraArgs={"ContentType": content_type},
    )
    return key


def delete_object(key: str) -> None:
    _get_client().delete_object(Bucket=_bucket(), Key=key)
