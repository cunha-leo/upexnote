from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..dependencies import get_reset_service
from ..schemas import (
    GenericAccepted,
    ResetComplete,
    ResetCompleted,
    ResetRequest,
    ResetVerified,
    ResetVerify,
)
from ..service import PasswordResetService, ResetFlowError


router = APIRouter(prefix="/auth/reset", tags=["password-reset"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/request", response_model=GenericAccepted, status_code=status.HTTP_202_ACCEPTED)
def request_reset(
    payload: ResetRequest,
    request: Request,
    service: PasswordResetService = Depends(get_reset_service),
) -> GenericAccepted:
    return GenericAccepted(
        message=service.request_reset(payload.email, _client_ip(request))
    )


@router.post("/verify", response_model=ResetVerified)
def verify_reset(
    payload: ResetVerify,
    service: PasswordResetService = Depends(get_reset_service),
) -> ResetVerified:
    try:
        token, expires_in = service.verify_code(payload.email, payload.code)
    except ResetFlowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return ResetVerified(reset_token=token, expires_in=expires_in)


@router.post("/complete", response_model=ResetCompleted)
def complete_reset(
    payload: ResetComplete,
    service: PasswordResetService = Depends(get_reset_service),
) -> ResetCompleted:
    try:
        service.complete_reset(payload.email, payload.reset_token, payload.new_password)
    except ResetFlowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return ResetCompleted()
