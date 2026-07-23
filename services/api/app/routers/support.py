"""Support API: isolated case system, not an e-mail inbox facade."""

from __future__ import annotations

from typing import Any, Literal
from pathlib import Path
import hashlib
import re
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from ..dependencies import get_support_repository
from ..support_db import PostgresSupportRepository
from ..dependencies import get_admin_elevation_service
from ..admin_service import AdminElevationService
from ..config import get_settings
from ..emailer import SmtpResetMailer


router = APIRouter(prefix="/support", tags=["support"])


class SupportIdentity(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    username: str = Field(min_length=2, max_length=80, pattern=r"^[a-zA-Z0-9._-]+$")
    display_name: str | None = Field(default=None, max_length=160)
    client_secret: str = Field(min_length=32, max_length=256)


class CreateTicket(SupportIdentity):
    subject: str = Field(min_length=4, max_length=240)
    body: str = Field(min_length=8, max_length=20_000)
    category: str = Field(default="general", pattern=r"^[a-z_]{2,40}$")
    priority: Literal["low", "normal", "high"] = "normal"
    app_version: str | None = Field(default=None, max_length=64)
    platform: str | None = Field(default=None, max_length=80)
    locale: str | None = Field(default=None, max_length=16)
    context: dict[str, Any] = Field(default_factory=dict)


class TicketAccess(SupportIdentity):
    ticket_id: int = Field(ge=1)


class AddComment(TicketAccess):
    body: str = Field(min_length=1, max_length=20_000)


class AdminAccess(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    elevation_token: str = Field(min_length=20, max_length=1024)


class AdminTicketAccess(AdminAccess):
    ticket_id: int = Field(ge=1)


class AdminComment(AdminTicketAccess):
    body: str = Field(min_length=1, max_length=20_000)


class AdminStatus(AdminTicketAccess):
    status: Literal["open", "in_progress", "pending_customer", "resolved", "closed"]
    reason: str | None = Field(default=None, max_length=500)


class AdminAssignment(AdminTicketAccess):
    assignee_email: str | None = Field(default=None, max_length=320)
    reason: str | None = Field(default=None, max_length=500)


def _identity(payload: SupportIdentity, repo: PostgresSupportRepository) -> dict[str, Any]:
    identity = repo.identity(email=payload.email.lower(), username=payload.username.lower(), display_name=payload.display_name, client_secret=payload.client_secret)
    if not identity:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="support_identity_unavailable")
    return identity


def _deliver(ticket_id: int, repo: PostgresSupportRepository) -> None:
    """Best effort notification dispatch. The durable queue is the record."""
    mailer = SmtpResetMailer(get_settings())
    for item in repo.pending_notifications(ticket_id):
        payload = item["payload"] or {}
        number, subject = payload.get("ticket_number", "UpexNote"), payload.get("subject", "Support")
        try:
            if item["notification_type"] == "ticket_received":
                mailer.send_support_message(item["recipient"], f"[{number}] Support request received", "We received your support request", f"Ticket {number}: {subject}")
            elif item["notification_type"] == "ticket_reply":
                mailer.send_support_message(item["recipient"], f"[{number}] UpexNote Support replied", "UpexNote Support replied", f"Ticket {number}: {subject}")
            else:
                mailer.send_support_message(item["recipient"], f"[{number}] New support request", "New UpexNote support request", f"Ticket {number}: {subject}")
            repo.complete_notification(item["id"])
        except Exception:
            repo.complete_notification(item["id"], "delivery_failed")


@router.post("/identity")
def establish_identity(payload: SupportIdentity, repo: PostgresSupportRepository = Depends(get_support_repository)) -> dict[str, Any]:
    """Establishes a desktop-local opaque identity without account passwords."""
    identity = _identity(payload, repo)
    return {"ok": True, "identity": {"email": identity["email"], "username": identity["username"], "display_name": identity["display_name"]}}


@router.post("/tickets", status_code=status.HTTP_201_CREATED)
def create_ticket(payload: CreateTicket, repo: PostgresSupportRepository = Depends(get_support_repository)) -> dict[str, Any]:
    identity = _identity(payload, repo)
    ticket = repo.create_ticket(identity["id"], payload.model_dump(exclude={"email", "username", "display_name", "client_secret"}))
    repo.queue_notification(ticket["id"], get_settings().support_admin_email, "new_ticket", {"ticket_number": ticket["ticket_number"], "subject": payload.subject})
    _deliver(ticket["id"], repo)
    return {"ok": True, "ticket": ticket}


@router.post("/tickets/list")
def customer_tickets(payload: SupportIdentity, repo: PostgresSupportRepository = Depends(get_support_repository)) -> dict[str, Any]:
    identity = _identity(payload, repo)
    return {"ok": True, "tickets": repo.list_tickets(identity["id"])}


@router.post("/tickets/detail")
def customer_ticket_detail(payload: TicketAccess, repo: PostgresSupportRepository = Depends(get_support_repository)) -> dict[str, Any]:
    identity = _identity(payload, repo)
    ticket = repo.ticket_detail(payload.ticket_id, identity["id"])
    if not ticket: raise HTTPException(status_code=404, detail="ticket_not_found")
    return {"ok": True, "ticket": ticket}


@router.post("/tickets/comment")
def customer_comment(payload: AddComment, repo: PostgresSupportRepository = Depends(get_support_repository)) -> dict[str, Any]:
    identity = _identity(payload, repo)
    comment = repo.add_comment(payload.ticket_id, body=payload.body, author_kind="customer", author_identity_id=identity["id"], author_label=identity.get("display_name"))
    if not comment: raise HTTPException(status_code=404, detail="ticket_not_found")
    return {"ok": True, "comment": comment}


def _admin(payload: AdminAccess, service: AdminElevationService, repo: PostgresSupportRepository) -> dict[str, Any]:
    if not service.validate_session(payload.email, payload.elevation_token).valid:
        raise HTTPException(status_code=403, detail="mfa_required")
    return repo.provision_staff_identity(email=payload.email, role="admin")


@router.post("/admin/tickets")
def admin_tickets(payload: AdminAccess, repo: PostgresSupportRepository = Depends(get_support_repository), admin: AdminElevationService = Depends(get_admin_elevation_service)) -> dict[str, Any]:
    _admin(payload, admin, repo)
    return {"ok": True, "tickets": repo.list_tickets()}


@router.post("/admin/tickets/detail")
def admin_ticket_detail(payload: AdminTicketAccess, repo: PostgresSupportRepository = Depends(get_support_repository), admin: AdminElevationService = Depends(get_admin_elevation_service)) -> dict[str, Any]:
    _admin(payload, admin, repo)
    ticket = repo.ticket_detail(payload.ticket_id)
    if not ticket: raise HTTPException(status_code=404, detail="ticket_not_found")
    return {"ok": True, "ticket": ticket}


@router.post("/admin/tickets/comment")
def admin_comment(payload: AdminComment, repo: PostgresSupportRepository = Depends(get_support_repository), admin: AdminElevationService = Depends(get_admin_elevation_service)) -> dict[str, Any]:
    actor = _admin(payload, admin, repo)
    comment = repo.add_comment(payload.ticket_id, body=payload.body, author_kind="admin", author_identity_id=actor["id"], author_label=actor.get("display_name") or actor["email"])
    if not comment: raise HTTPException(status_code=404, detail="ticket_not_found")
    ticket = repo.ticket_detail(payload.ticket_id)
    if ticket:
        repo.queue_notification(payload.ticket_id, ticket["email"], "ticket_reply", {"ticket_number": ticket["ticket_number"], "subject": ticket["subject"]})
        _deliver(payload.ticket_id, repo)
    return {"ok": True, "comment": comment}


@router.post("/admin/tickets/status")
def admin_status(payload: AdminStatus, repo: PostgresSupportRepository = Depends(get_support_repository), admin: AdminElevationService = Depends(get_admin_elevation_service)) -> dict[str, Any]:
    actor = _admin(payload, admin, repo)
    ticket = repo.transition_status(payload.ticket_id, to_status=payload.status, actor_kind="admin", actor_identity_id=actor["id"], reason=payload.reason)
    if not ticket: raise HTTPException(status_code=404, detail="ticket_not_found")
    return {"ok": True, "ticket": ticket}


@router.post("/admin/tickets/assignment")
def admin_assignment(payload: AdminAssignment, repo: PostgresSupportRepository = Depends(get_support_repository), admin: AdminElevationService = Depends(get_admin_elevation_service)) -> dict[str, Any]:
    actor = _admin(payload, admin, repo)
    assignee = repo.provision_staff_identity(email=payload.assignee_email, role="support") if payload.assignee_email else None
    ticket = repo.assign_ticket(payload.ticket_id, assignee_identity_id=assignee["id"] if assignee else None, assigned_by_identity_id=actor["id"], reason=payload.reason)
    if not ticket: raise HTTPException(status_code=404, detail="ticket_not_found")
    return {"ok": True, "ticket": ticket}


_EVIDENCE_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "application/pdf": ".pdf"}


@router.post("/tickets/attachment", status_code=status.HTTP_201_CREATED)
async def add_attachment(
    email: str = Form(...), username: str = Form(...), client_secret: str = Form(...), ticket_id: int = Form(...),
    display_name: str | None = Form(default=None), file: UploadFile = File(...),
    repo: PostgresSupportRepository = Depends(get_support_repository),
) -> dict[str, Any]:
    """Accept a bounded evidence file into the VPS spool, never the database."""
    identity_payload = SupportIdentity(email=email, username=username, display_name=display_name, client_secret=client_secret)
    identity = _identity(identity_payload, repo)
    content_type = (file.content_type or "").lower()
    extension = _EVIDENCE_TYPES.get(content_type)
    if not extension:
        raise HTTPException(status_code=415, detail="unsupported_evidence_type")
    original_name = Path(file.filename or "evidence").name
    original_name = re.sub(r"[^A-Za-z0-9._-]+", "_", original_name)[:180] or f"evidence{extension}"
    settings = get_settings()
    folder = Path(settings.support_spool_dir) / str(ticket_id)
    folder.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{extension}"
    destination = folder / stored_name
    digest, total = hashlib.sha256(), 0
    try:
        with destination.open("xb") as out:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > settings.support_attachment_max_bytes:
                    raise HTTPException(status_code=413, detail="evidence_too_large")
                digest.update(chunk); out.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
    attachment = repo.add_attachment(ticket_id, identity_id=identity["id"], original_filename=original_name, stored_filename=stored_name, content_type=content_type, byte_size=total, sha256=digest.hexdigest(), spool_path=str(destination))
    if not attachment:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=404, detail="ticket_not_found")
    return {"ok": True, "attachment": attachment}
