import re
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict

NAME_RE = re.compile(r"^[A-Za-z]+([\-' ][A-Za-z]+)*$")
VALID_SEX = {"Male", "Female", "Other", "Decline to Answer"}
VALID_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN",
    "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV",
    "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN",
    "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
}


def _digits_only(v: str) -> str:
    return re.sub(r"\D", "", v or "")


def _validate_name(v: str, field: str) -> str:
    v = (v or "").strip()
    if not (1 <= len(v) <= 50):
        raise ValueError(f"{field} must be 1-50 characters")
    if not NAME_RE.match(v):
        raise ValueError(f"{field} may only contain letters, hyphens, and apostrophes")
    return v


def _validate_us_phone(v: str, field: str) -> str:
    digits = _digits_only(v)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        raise ValueError(f"{field} must be a valid 10-digit U.S. phone number")
    return digits


def _validate_zip(v: str) -> str:
    v = (v or "").strip()
    if not re.match(r"^\d{5}(-\d{4})?$", v):
        raise ValueError("zip_code must be in 5-digit or ZIP+4 (12345 or 12345-6789) format")
    return v


def _validate_dob(v: date) -> date:
    if v > date.today():
        raise ValueError("date_of_birth cannot be in the future")
    if v.year < 1900:
        raise ValueError("date_of_birth is not plausible")
    return v


class PatientBase(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date
    sex: str
    phone_number: str
    address_line_1: str
    city: str
    state: str
    zip_code: str

    email: Optional[EmailStr] = None
    address_line_2: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_member_id: Optional[str] = None
    preferred_language: Optional[str] = "English"
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None

    @field_validator("first_name")
    @classmethod
    def v_first(cls, v):
        return _validate_name(v, "first_name")

    @field_validator("last_name")
    @classmethod
    def v_last(cls, v):
        return _validate_name(v, "last_name")

    @field_validator("date_of_birth")
    @classmethod
    def v_dob(cls, v):
        return _validate_dob(v)

    @field_validator("sex")
    @classmethod
    def v_sex(cls, v):
        if v not in VALID_SEX:
            raise ValueError(f"sex must be one of {sorted(VALID_SEX)}")
        return v

    @field_validator("phone_number")
    @classmethod
    def v_phone(cls, v):
        return _validate_us_phone(v, "phone_number")

    @field_validator("emergency_contact_phone")
    @classmethod
    def v_ec_phone(cls, v):
        if v is None or v == "":
            return None
        return _validate_us_phone(v, "emergency_contact_phone")

    @field_validator("state")
    @classmethod
    def v_state(cls, v):
        v = (v or "").strip().upper()
        if v not in VALID_STATES:
            raise ValueError("state must be a valid 2-letter U.S. state abbreviation")
        return v

    @field_validator("zip_code")
    @classmethod
    def v_zip(cls, v):
        return _validate_zip(v)

    @field_validator("city")
    @classmethod
    def v_city(cls, v):
        v = (v or "").strip()
        if not (1 <= len(v) <= 100):
            raise ValueError("city must be 1-100 characters")
        return v


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    """All fields optional to support partial updates (PUT with partial body)."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    sex: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_member_id: Optional[str] = None
    preferred_language: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None

    @field_validator("first_name")
    @classmethod
    def v_first(cls, v):
        return v if v is None else _validate_name(v, "first_name")

    @field_validator("last_name")
    @classmethod
    def v_last(cls, v):
        return v if v is None else _validate_name(v, "last_name")

    @field_validator("date_of_birth")
    @classmethod
    def v_dob(cls, v):
        return v if v is None else _validate_dob(v)

    @field_validator("sex")
    @classmethod
    def v_sex(cls, v):
        if v is None:
            return v
        if v not in VALID_SEX:
            raise ValueError(f"sex must be one of {sorted(VALID_SEX)}")
        return v

    @field_validator("phone_number")
    @classmethod
    def v_phone(cls, v):
        return v if v is None else _validate_us_phone(v, "phone_number")

    @field_validator("emergency_contact_phone")
    @classmethod
    def v_ec_phone(cls, v):
        return v if v is None else _validate_us_phone(v, "emergency_contact_phone")

    @field_validator("state")
    @classmethod
    def v_state(cls, v):
        if v is None:
            return v
        v = v.strip().upper()
        if v not in VALID_STATES:
            raise ValueError("state must be a valid 2-letter U.S. state abbreviation")
        return v

    @field_validator("zip_code")
    @classmethod
    def v_zip(cls, v):
        return v if v is None else _validate_zip(v)


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    patient_id: str
    first_name: str
    last_name: str
    date_of_birth: date
    sex: str
    phone_number: str
    email: Optional[str] = None
    address_line_1: str
    address_line_2: Optional[str] = None
    city: str
    state: str
    zip_code: str
    insurance_provider: Optional[str] = None
    insurance_member_id: Optional[str] = None
    preferred_language: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
