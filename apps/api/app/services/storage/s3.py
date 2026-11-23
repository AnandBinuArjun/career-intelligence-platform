from functools import lru_cache
from pathlib import Path
from threading import Lock

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings

_bucket_checked = False
_bucket_lock = Lock()


def _local_root() -> Path:
    root = Path(settings.local_storage_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_local_path(object_key: str) -> Path:
    root = _local_root()
    cleaned = object_key.lstrip("/").replace("\\", "/")
    target = (root / cleaned).resolve()
    if root not in target.parents and target != root:
        raise ValueError("Invalid storage object key")
    return target


@lru_cache(maxsize=1)
def s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        use_ssl=settings.s3_use_ssl,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def ensure_bucket() -> None:
    global _bucket_checked
    if settings.storage_backend == "local":
        _local_root()
        return
    if _bucket_checked:
        return
    with _bucket_lock:
        if _bucket_checked:
            return
        client = s3_client()
        try:
            client.head_bucket(Bucket=settings.s3_bucket)
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code not in {"404", "NoSuchBucket", "NotFound"}:
                raise
            create_kwargs: dict[str, object] = {"Bucket": settings.s3_bucket}
            if settings.s3_region and settings.s3_region != "us-east-1":
                create_kwargs["CreateBucketConfiguration"] = {
                    "LocationConstraint": settings.s3_region
                }
            client.create_bucket(**create_kwargs)
        _bucket_checked = True


def create_upload_url(object_key: str, content_type: str) -> str:
    ensure_bucket()
    if settings.storage_backend == "local":
        # Local dev fallback does not expose public URLs; use POST /api/v1/resumes/upload directly.
        return f"local-private://{object_key}"
    return s3_client().generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.s3_bucket, "Key": object_key, "ContentType": content_type},
        ExpiresIn=settings.presigned_upload_ttl_seconds,
    )


def read_uploaded_object(object_key: str) -> bytes:
    max_read = settings.max_upload_mb * 1024 * 1024 + 1
    if settings.storage_backend == "local":
        path = _safe_local_path(object_key)
        with path.open("rb") as fh:
            return fh.read(max_read)
    response = s3_client().get_object(Bucket=settings.s3_bucket, Key=object_key)
    return response["Body"].read(max_read)


def delete_object(object_key: str) -> None:
    if not object_key:
        return
    if settings.storage_backend == "local":
        path = _safe_local_path(object_key)
        if path.exists():
            path.unlink()
        return
    try:
        s3_client().delete_object(Bucket=settings.s3_bucket, Key=object_key)
    except ClientError:
        # Deletion is best-effort when cleaning up rejected or already-deleted keys.
        return


def put_validated_object(object_key: str, data: bytes, content_type: str) -> None:
    ensure_bucket()
    if settings.storage_backend == "local":
        path = _safe_local_path(object_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return
    s3_client().put_object(
        Bucket=settings.s3_bucket,
        Key=object_key,
        Body=data,
        ContentType=content_type,
    )
