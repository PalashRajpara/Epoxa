"""
Services package for Epoxa core.
"""

from epoxa_core.services.appointment_service import AppointmentService, generate_confirmation_code
from epoxa_core.services.audit_service import AuditService
from epoxa_core.services.call_session_service import CallSessionService
from epoxa_core.services.customer_service import CustomerService, normalize_to_e164
from epoxa_core.services.kb_service import KBService
from epoxa_core.services.ticket_service import TicketService

__all__ = [
    "AppointmentService",
    "generate_confirmation_code",
    "AuditService",
    "CallSessionService",
    "CustomerService",
    "normalize_to_e164",
    "TicketService",
    "KBService",
]
