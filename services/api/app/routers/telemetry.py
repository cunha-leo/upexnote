from fastapi import APIRouter, HTTPException, status


router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.post("/events", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def ingest_event() -> None:
    """Reserved for authenticated installation telemetry."""
    raise HTTPException(status_code=501, detail="not_implemented")
