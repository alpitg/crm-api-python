from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.utils.azure_storage import generate_upload_sas

router = APIRouter()


ALLOWED_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/jpg"
}


class UploadRequest(BaseModel):
    fileName: str
    contentType: str

class UploadResponse(BaseModel):
    uploadUrl: str
    blobUrl: str
    blobName: str

@router.post("/upload-url")
def upload_url(request: UploadRequest, response_model=UploadResponse):

    if request.contentType not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type"
        )

    return generate_upload_sas(
        request.fileName,
        request.contentType
    )