from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..admin_service import AdminElevationService, AdminFlowError
from ..dependencies import get_admin_elevation_service
from ..schemas import (
    AdminChallenge,
    AdminChallengeAccepted,
    AdminRevoked,
    AdminTokenPayload,
    AdminTotpConfirm,
    AdminTotpConfirmed,
    AdminTotpEnrollment,
    AdminValidation,
    AdminVerified,
    AdminVerify,
)


router = APIRouter(prefix="/admin/elevation", tags=["admin-elevation"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/challenge", response_model=AdminChallengeAccepted, status_code=status.HTTP_202_ACCEPTED)
def create_admin_challenge(
    payload: AdminChallenge,
    request: Request,
    service: AdminElevationService = Depends(get_admin_elevation_service),
) -> AdminChallengeAccepted:
    message, factor = service.request_challenge(
        payload.email, payload.admin_secret, _client_ip(request), payload.prefer_email
    )
    return AdminChallengeAccepted(message=message, factor=factor)


@router.post("/verify", response_model=AdminVerified)
def verify_admin_factor(
    payload: AdminVerify,
    service: AdminElevationService = Depends(get_admin_elevation_service),
) -> AdminVerified:
    try:
        token, expires_in, factor, enrolled = service.verify_factor(payload.email, payload.code)
    except AdminFlowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return AdminVerified(
        elevation_token=token,
        expires_in=expires_in,
        factor=factor,
        totp_enrolled=enrolled,
    )


@router.post("/validate", response_model=AdminValidation)
def validate_admin_session(
    payload: AdminTokenPayload,
    service: AdminElevationService = Depends(get_admin_elevation_service),
) -> AdminValidation:
    result = service.validate_session(payload.email, payload.elevation_token)
    return AdminValidation(
        valid=result.valid,
        user_id=result.user_id,
        expires_in=result.expires_in,
        totp_enrolled=result.totp_enrolled,
    )


@router.post("/revoke", response_model=AdminRevoked)
def revoke_admin_session(
    payload: AdminTokenPayload,
    service: AdminElevationService = Depends(get_admin_elevation_service),
) -> AdminRevoked:
    service.revoke_session(payload.email, payload.elevation_token)
    return AdminRevoked()


@router.post("/totp/enroll", response_model=AdminTotpEnrollment)
def begin_totp_enrollment(
    payload: AdminTokenPayload,
    service: AdminElevationService = Depends(get_admin_elevation_service),
) -> AdminTotpEnrollment:
    try:
        qr, manual_key, expires_in = service.begin_totp_enrollment(
            payload.email, payload.elevation_token
        )
    except AdminFlowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return AdminTotpEnrollment(qr_data_url=qr, manual_key=manual_key, expires_in=expires_in)


@router.post("/totp/confirm", response_model=AdminTotpConfirmed)
def confirm_totp_enrollment(
    payload: AdminTotpConfirm,
    service: AdminElevationService = Depends(get_admin_elevation_service),
) -> AdminTotpConfirmed:
    try:
        service.confirm_totp_enrollment(payload.email, payload.elevation_token, payload.code)
    except AdminFlowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return AdminTotpConfirmed()
