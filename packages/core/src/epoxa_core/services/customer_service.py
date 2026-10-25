"""
Customer service implementing phone normalization, identity verification, and privacy guards.
"""

import uuid
from typing import Any, Dict, List, Optional
import phonenumbers
from epoxa_core.exceptions import ConflictError, EntityNotFoundError, ValidationError
from epoxa_core.models.entities import Customer
from epoxa_core.uow import UnitOfWork


def normalize_to_e164(raw_phone: str, default_region: str = "IN") -> str:
    """Normalizes raw input or spoken digits into a standardized E.164 format (+919876543210)."""
    # Clean spoken characters and common filler words
    cleaned = "".join(char for char in raw_phone if char.isdigit() or char == "+")

    try:
        parsed = phonenumbers.parse(cleaned, default_region)
        if not phonenumbers.is_valid_number(parsed):
            raise ValidationError(f"Invalid phone number format for region '{default_region}'.")
        return str(phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164))
    except Exception as e:
        raise ValidationError(f"Could not parse phone number '{raw_phone}': {str(e)}") from e


class CustomerService:
    """Handles customer lookup, creation, and privacy management."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def verify_by_phone(
        self,
        organization_id: uuid.UUID,
        raw_phone: str,
        default_region: str = "IN",
    ) -> Optional[Customer]:
        """Looks up a customer by phone number, returning minimal details to guard privacy."""
        normalized_phone = normalize_to_e164(raw_phone, default_region=default_region)
        customer = await self.uow.customers.get_by_phone(organization_id, normalized_phone)
        return customer

    async def register_customer(
        self,
        organization_id: uuid.UUID,
        name: str,
        phone: str,
        email: Optional[str] = None,
        tier: str = "Standard",
        default_region: str = "IN",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Customer:
        """Registers a new customer profile, verifying uniqueness."""
        name_clean = name.strip()
        if not name_clean:
            raise ValidationError("Customer name cannot be empty.")

        phone_e164 = normalize_to_e164(phone, default_region=default_region)

        # Check if active customer already exists
        existing = await self.uow.customers.get_by_phone(organization_id, phone_e164)
        if existing:
            raise ConflictError(f"Customer with phone number '{phone_e164}' already exists.")

        customer = Customer(
            organization_id=organization_id,
            name=name_clean,
            phone_e164=phone_e164,
            email=email.strip().lower() if email else None,
            tier=tier,
            metadata_=metadata or {},
        )
        self.uow.customers.add(customer)
        await self.uow.commit()
        return customer

    async def anonymize_customer(
        self,
        organization_id: uuid.UUID,
        customer_id: uuid.UUID,
    ) -> Customer:
        """Sanitizes customer PII for GDPR compliance while keeping appointment history intact."""
        customer = await self.uow.customers.get_by_id(customer_id)
        if not customer or customer.organization_id != organization_id:
            raise EntityNotFoundError("Customer", customer_id)

        anonymized = await self.uow.customers.anonymize(customer_id)
        if not anonymized:
            raise EntityNotFoundError("Customer", customer_id)

        await self.uow.commit()
        return anonymized

    async def list_customers(
        self,
        organization_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Customer]:
        return await self.uow.customers.list_by_org(organization_id, limit=limit, offset=offset)
