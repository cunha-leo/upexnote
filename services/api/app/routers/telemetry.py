from fastapi import APIRouter, Depends, Header, HTTPException, status

from ..dependencies import get_telemetry_service
from ..schemas import TelemetryAccepted, TelemetryEvent
from ..telemetry_service import TelemetryService
from ..dependencies import get_installation_token_service
from ..token_service import InstallationTokenService


router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.post("/events", response_model=TelemetryAccepted, status_code=status.HTTP_202_ACCEPTED)
def ingest_event(payload: TelemetryEvent, authorization: str | None = Header(default=None), service: TelemetryService = Depends(get_telemetry_service), token_service: InstallationTokenService = Depends(get_installation_token_service)) -> TelemetryAccepted:
    token = authorization.removeprefix("Bearer ") if authorization else ""
    if not token_service.valid(payload.installation_id, token):
        raise HTTPException(status_code=401, detail="invalid_installation_token")
    service.ingest(payload)
    return TelemetryAccepted()
