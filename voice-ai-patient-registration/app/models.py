import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Date, DateTime
from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Patient(Base):
    """
    Standard-minimum-demographic-dataset patient record.
    Soft-delete is implemented via `deleted_at` (NULL = active record).
    """
    __tablename__ = "patients"

    patient_id = Column(String, primary_key=True, default=_uuid)

    # Required
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    sex = Column(String(20), nullable=False)  # Male | Female | Other | Decline to Answer
    phone_number = Column(String(10), nullable=False, index=True)  # normalized to 10 digits
    address_line_1 = Column(String(200), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(2), nullable=False)
    zip_code = Column(String(10), nullable=False)  # 5-digit or ZIP+4

    # Optional
    email = Column(String(255), nullable=True)
    address_line_2 = Column(String(200), nullable=True)
    insurance_provider = Column(String(200), nullable=True)
    insurance_member_id = Column(String(50), nullable=True)
    preferred_language = Column(String(50), nullable=True, default="English")
    emergency_contact_name = Column(String(200), nullable=True)
    emergency_contact_phone = Column(String(10), nullable=True)

    # Auto
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
