from fastapi import APIRouter, Depends, HTTPException, status
from ..dependencies import get_installation_token_service
from ..schemas import InstallationToken, InstallationTokenExchange
from ..token_service import InstallationTokenService


router = APIRouter(prefix="/tokens", tags=["phase-2"])


@router.post("/exchange", response_model=InstallationToken, status_code=status.HTTP_201_CREATED)
def exchange_token(payload: InstallationTokenExchange, service: InstallationTokenService = Depends(get_installation_token_service)) -> InstallationToken:
    if not payload.consent: raise HTTPException(status_code=403, detail="telemetry_consent_required")
    token, expires_in = service.exchange(payload.installation_id)
    return InstallationToken(access_token=token, expires_in=expires_in)
