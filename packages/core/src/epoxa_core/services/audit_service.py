"""
Audit service implementing append-only compliance logging.
"""

import uuid
from typing import Any, Dict, List, Optional
from epoxa_core.models.entities import AuditLog
from epoxa_core.uow import UnitOfWork


class AuditService:
    """Manages append-only security and operational audit trails."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def log_event(
        self,
        organization_id: uuid.UUID,
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        actor_profile_id: Optional[uuid.UUID] = None,
        ip: Optional[str] = None,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Appends a new audit log entry."""
        log = AuditLog(
            organization_id=organization_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_profile_id=actor_profile_id,
            ip=ip,
            request_id=request_id,
            metadata_=metadata or {},
        )
        self.uow.audit_logs.add(log)
        await self.uow.commit()
        return log

    async def list_logs(
        self,
        organization_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        return await self.uow.audit_logs.list_by_org(organization_id, limit=limit, offset=offset)
