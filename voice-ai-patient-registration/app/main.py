import logging
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.database import engine, Base, get_db
from app import crud, schemas
from app.vapi_webhook import router as vapi_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("patient_registration")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Voice AI Patient Registration API", version="1.0.0")
app.include_router(vapi_router)
app.mount("/static", StaticFiles(directory="static"), name="static")


def envelope(data=None, error=None):
    return {"data": data, "error": error}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(status_code=422, content=envelope(error=exc.errors()))


@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(status_code=422, content=envelope(error=str(exc)))


@app.get("/")
def dashboard():
    """Simple bonus dashboard UI."""
    return FileResponse("static/dashboard.html")


@app.get("/health")
def health():
    return envelope(data={"status": "ok"})


@app.get("/patients")
def list_patients(
    last_name: Optional[str] = Query(None),
    date_of_birth: Optional[str] = Query(None),
    phone_number: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    patients = crud.list_patients(
        db, last_name=last_name, date_of_birth=date_of_birth, phone_number=phone_number
    )
    return envelope(data=[schemas.PatientOut.model_validate(p).model_dump(mode="json") for p in patients])


@app.get("/patients/{patient_id}")
def get_patient(patient_id: str, db: Session = Depends(get_db)):
    patient = crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=envelope(error="Patient not found"))
    return envelope(data=schemas.PatientOut.model_validate(patient).model_dump(mode="json"))


@app.post("/patients", status_code=201)
def create_patient(payload: schemas.PatientCreate, db: Session = Depends(get_db)):
    try:
        patient = crud.create_patient(db, payload)
    except Exception as e:
        logger.exception("Failed to create patient")
        raise HTTPException(status_code=500, detail=envelope(error=f"Database write failed: {e}"))
    logger.info("PATIENT_CREATED payload=%s", payload.model_dump(mode="json"))
    return envelope(data=schemas.PatientOut.model_validate(patient).model_dump(mode="json"))


@app.put("/patients/{patient_id}")
def update_patient(patient_id: str, payload: schemas.PatientUpdate, db: Session = Depends(get_db)):
    patient = crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=envelope(error="Patient not found"))
    try:
        patient = crud.update_patient(db, patient, payload)
    except Exception as e:
        logger.exception("Failed to update patient")
        raise HTTPException(status_code=500, detail=envelope(error=f"Database write failed: {e}"))
    logger.info("PATIENT_UPDATED id=%s", patient_id)
    return envelope(data=schemas.PatientOut.model_validate(patient).model_dump(mode="json"))


@app.delete("/patients/{patient_id}")
def delete_patient(patient_id: str, db: Session = Depends(get_db)):
    patient = crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=envelope(error="Patient not found"))
    crud.soft_delete_patient(db, patient)
    logger.info("PATIENT_SOFT_DELETED id=%s", patient_id)
    return envelope(data={"patient_id": patient_id, "deleted": True})
