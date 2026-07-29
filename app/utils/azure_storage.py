import uuid

from datetime import datetime, timedelta, timezone

from azure.storage.blob import (
    generate_blob_sas,
    BlobSasPermissions
)

from config import settings


def generate_upload_sas(
    original_filename: str,
    content_type: str
):
    """
    Returns:
        upload_url
        blob_url
        blob_name
    """

    extension = original_filename.split(".")[-1].lower()

    blob_name = f"products/{uuid.uuid4()}.{extension}"

    sas_token = generate_blob_sas(
        account_name=settings.AZURE_STORAGE_ACCOUNT_NAME,
        container_name=settings.AZURE_STORAGE_CONTAINER,
        blob_name=blob_name,

        account_key=settings.AZURE_STORAGE_ACCOUNT_KEY,

        permission=BlobSasPermissions(write=True),

        expiry=datetime.now(timezone.utc) + timedelta(minutes=10),

        content_type=content_type,
    )

    upload_url = (
        f"https://{settings.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/"
        f"{settings.AZURE_STORAGE_CONTAINER}/{blob_name}?{sas_token}"
    )

    blob_url = (
        f"https://{settings.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/"
        f"{settings.AZURE_STORAGE_CONTAINER}/{blob_name}"
    )

    return {
        "uploadUrl": upload_url,
        "blobUrl": blob_url,
        "blobName": blob_name
    }