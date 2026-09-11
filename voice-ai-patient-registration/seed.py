"""Run with: python seed.py
Inserts 2 demo patients if they don't already exist (matched by phone number)."""
from datetime import date
from app.database import SessionLocal, engine, Base
from app import crud, schemas

Base.metadata.create_all(bind=engine)

SEED_PATIENTS = [
    schemas.PatientCreate(
        first_name="Jane", last_name="Doe", date_of_birth=date(1990, 4, 12),
        sex="Female", phone_number="5551234567", email="jane.doe@example.com",
        address_line_1="123 Main St", city="Austin", state="TX", zip_code="78701",
        insurance_provider="Blue Cross", insurance_member_id="BC123456",
        preferred_language="English",
    ),
    schemas.PatientCreate(
        first_name="Carlos", last_name="Mendez", date_of_birth=date(1985, 11, 2),
        sex="Male", phone_number="5559876543", email="carlos.mendez@example.com",
        address_line_1="456 Oak Ave", address_line_2="Apt 3B", city="Phoenix",
        state="AZ", zip_code="85001", preferred_language="Spanish",
        emergency_contact_name="Maria Mendez", emergency_contact_phone="5551112222",
    ),
]

if __name__ == "__main__":
    db = SessionLocal()
    try:
        for p in SEED_PATIENTS:
            existing = crud.get_patient_by_phone(db, p.phone_number)
            if existing:
                print(f"Skipping {p.first_name} {p.last_name}, already exists.")
                continue
            created = crud.create_patient(db, p)
            print(f"Seeded {created.first_name} {created.last_name} ({created.patient_id})")
    finally:
        db.close()
