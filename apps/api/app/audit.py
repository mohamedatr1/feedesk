from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from .deps import client_ip
from .models import AuditEvent
from .privacy import redact_audit_payload


def record_audit(
    db: Session,
    *,
    request: Request | None,
    actor_user_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_data=redact_audit_payload(before),
        after_data=redact_audit_payload(after),
        request_id=getattr(request.state, "request_id", None) if request else None,
        ip_address=client_ip(request) if request else None,
    )
    db.add(event)
    return event
