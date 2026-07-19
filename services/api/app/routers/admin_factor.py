from fastapi import APIRouter, HTTPException, status


router = APIRouter(prefix="/admin/elevation", tags=["admin-elevation"])


@router.post("/challenge", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def create_admin_challenge() -> None:
    """Reserved for the e-mail/TOTP third factor."""
    raise HTTPException(status_code=501, detail="not_implemented")
