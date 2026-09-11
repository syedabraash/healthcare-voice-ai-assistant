from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import Patient
from app import schemas


def create_patient(db: Session, data: schemas.PatientCreate) -> Patient:
    patient = Patient(**data.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def get_patient(db: Session, patient_id: str, include_deleted: bool = False) -> Optional[Patient]:
    stmt = select(Patient).where(Patient.patient_id == patient_id)
    if not include_deleted:
        stmt = stmt.where(Patient.deleted_at.is_(None))
    return db.execute(stmt).scalar_one_or_none()


def get_patient_by_phone(db: Session, phone_number: str) -> Optional[Patient]:
    """Used by the voice agent's duplicate-detection tool call."""
    stmt = select(Patient).where(
        Patient.phone_number == phone_number, Patient.deleted_at.is_(None)
    )
    return db.execute(stmt).scalar_one_or_none()


def list_patients(
    db: Session,
    last_name: Optional[str] = None,
    date_of_birth: Optional[str] = None,
    phone_number: Optional[str] = None,
    include_deleted: bool = False,
):
    stmt = select(Patient)
    if not include_deleted:
        stmt = stmt.where(Patient.deleted_at.is_(None))
    if last_name:
        stmt = stmt.where(Patient.last_name.ilike(last_name))
    if date_of_birth:
        stmt = stmt.where(Patient.date_of_birth == date_of_birth)
    if phone_number:
        stmt = stmt.where(Patient.phone_number == phone_number)
    stmt = stmt.order_by(Patient.created_at.desc())
    return db.execute(stmt).scalars().all()


def update_patient(db: Session, patient: Patient, data: schemas.PatientUpdate) -> Patient:
    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(patient, field, value)
    patient.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(patient)
    return patient


def soft_delete_patient(db: Session, patient: Patient) -> Patient:
    patient.deleted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(patient)
    return patient
