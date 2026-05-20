from fastapi import APIRouter, Depends

from app.core.security import verify_copilot_api_key

router = APIRouter(dependencies=[Depends(verify_copilot_api_key)])


@router.post("/upload")
def upload_document():
    """Multipart file upload — stretch goal after text ingest."""
    return {
        "message": "Not implemented. Use POST /copilot/documents/ingest-text for MVP.",
    }
