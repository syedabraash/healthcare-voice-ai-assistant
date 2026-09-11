import os
import sys
import tempfile

# Use an isolated temp SQLite DB for tests, set BEFORE importing the app.
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db.name}"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)

VALID_PATIENT = {
    "first_name": "Jane",
    "last_name": "Doe",
    "date_of_birth": "1990-04-12",
    "sex": "Female",
    "phone_number": "555-123-4567",
    "email": "jane@example.com",
    "address_line_1": "123 Main St",
    "city": "Austin",
    "state": "tx",
    "zip_code": "78701",
}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "ok"


def test_create_patient_success():
    r = client.post("/patients", json=VALID_PATIENT)
    assert r.status_code == 201
    body = r.json()
    assert body["error"] is None
    assert body["data"]["phone_number"] == "5551234567"  # normalized, dashes stripped
    assert body["data"]["state"] == "TX"  # normalized to uppercase
    assert "patient_id" in body["data"]


def test_create_patient_invalid_phone():
    payload = dict(VALID_PATIENT, phone_number="123")
    r = client.post("/patients", json=payload)
    assert r.status_code == 422


def test_create_patient_future_dob():
    payload = dict(VALID_PATIENT, phone_number="5559990000", date_of_birth="2999-01-01")
    r = client.post("/patients", json=payload)
    assert r.status_code == 422


def test_create_patient_invalid_state():
    payload = dict(VALID_PATIENT, phone_number="5559990001", state="ZZ")
    r = client.post("/patients", json=payload)
    assert r.status_code == 422


def test_get_patient_by_id_and_404():
    r = client.post("/patients", json=dict(VALID_PATIENT, phone_number="5559990002"))
    patient_id = r.json()["data"]["patient_id"]

    got = client.get(f"/patients/{patient_id}")
    assert got.status_code == 200
    assert got.json()["data"]["first_name"] == "Jane"

    missing = client.get("/patients/does-not-exist")
    assert missing.status_code == 404


def test_list_patients_filter_by_last_name():
    client.post("/patients", json=dict(VALID_PATIENT, last_name="Smith", phone_number="5559990003"))
    r = client.get("/patients", params={"last_name": "Smith"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data) >= 1
    assert all(p["last_name"] == "Smith" for p in data)


def test_update_patient_partial():
    r = client.post("/patients", json=dict(VALID_PATIENT, phone_number="5559990004"))
    patient_id = r.json()["data"]["patient_id"]

    upd = client.put(f"/patients/{patient_id}", json={"email": "new@example.com"})
    assert upd.status_code == 200
    assert upd.json()["data"]["email"] == "new@example.com"
    assert upd.json()["data"]["first_name"] == "Jane"  # untouched fields preserved


def test_soft_delete_hides_from_list_but_keeps_record():
    r = client.post("/patients", json=dict(VALID_PATIENT, phone_number="5559990005"))
    patient_id = r.json()["data"]["patient_id"]

    dele = client.delete(f"/patients/{patient_id}")
    assert dele.status_code == 200

    # No longer appears in default listing
    listing = client.get("/patients", params={"phone_number": "5559990005"})
    assert listing.json()["data"] == []

    # But GET by id still 404s through the public API since it's soft-deleted
    got = client.get(f"/patients/{patient_id}")
    assert got.status_code == 404


def test_persistence_across_requests_simulates_second_call():
    """Mirrors the take-home's 'call back and data should still be there' requirement."""
    client.post("/patients", json=dict(VALID_PATIENT, last_name="Persisted", phone_number="5559990006"))
    r = client.get("/patients", params={"phone_number": "5559990006"})
    assert len(r.json()["data"]) == 1
    assert r.json()["data"][0]["last_name"] == "Persisted"
