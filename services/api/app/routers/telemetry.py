from fastapi import APIRouter, Depends, Header, HTTPException, status

from ..dependencies import get_telemetry_service, get_admin_elevation_service
from ..schemas import TelemetryAccepted, TelemetryEvent
from ..telemetry_service import TelemetryService
from ..dependencies import get_installation_token_service
from ..token_service import InstallationTokenService
from ..admin_service import AdminElevationService
from pydantic import BaseModel, Field


router = APIRouter(prefix="/telemetry", tags=["telemetry"])


class TelemetryOverviewRequest(BaseModel):
    email: str
    elevation_token: str
    days: int = Field(default=7, ge=1, le=90)


@router.post("/events", response_model=TelemetryAccepted, status_code=status.HTTP_202_ACCEPTED)
def ingest_event(payload: TelemetryEvent, authorization: str | None = Header(default=None), service: TelemetryService = Depends(get_telemetry_service), token_service: InstallationTokenService = Depends(get_installation_token_service)) -> TelemetryAccepted:
    token = authorization.removeprefix("Bearer ") if authorization else ""
    if not token_service.valid(payload.installation_id, token):
        raise HTTPException(status_code=401, detail="invalid_installation_token")
    service.ingest(payload)
    return TelemetryAccepted()


@router.post("/overview")
def telemetry_overview(payload: TelemetryOverviewRequest, telemetry: TelemetryService = Depends(get_telemetry_service), admin: AdminElevationService = Depends(get_admin_elevation_service)) -> dict:
    if not admin.validate_session(payload.email, payload.elevation_token).valid:
        raise HTTPException(status_code=403, detail="mfa_required")
    return telemetry.repository.overview(payload.days)
