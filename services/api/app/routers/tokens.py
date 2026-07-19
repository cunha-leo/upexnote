from fastapi import APIRouter, HTTPException, status


router = APIRouter(prefix="/tokens", tags=["phase-2"])


@router.post("/exchange", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def exchange_token() -> None:
    """Reserved for Phase 2 tokens and webhook authorization."""
    raise HTTPException(status_code=501, detail="not_implemented")
