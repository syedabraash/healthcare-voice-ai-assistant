"""
Adapter between Vapi (telephony + STT/TTS + LLM orchestration) and our data layer.

Why a separate adapter instead of pointing Vapi straight at /patients?
Vapi's "custom tool" webhook contract wraps calls in its own envelope
( {"message": {"toolCalls": [...]}} ) and expects a specific response
shape ( {"results": [{"toolCallId": ..., "result": ...}]} ). Keeping that
translation here means the core REST API in main.py stays a clean, generic
REST API that has no knowledge of Vapi at all -- any other voice platform
(Retell, Bland, a Twilio+custom-LLM stack) could reuse it unchanged.
"""
import os
import json
import logging
from datetime import date
from fastapi import APIRouter, Request, Header, HTTPException
from pydantic import ValidationError
from app.database import SessionLocal
from app import crud, schemas

logger = logging.getLogger("patient_registration")
router = APIRouter(prefix="/vapi", tags=["vapi"])

WEBHOOK_SECRET = os.getenv("VAPI_WEBHOOK_SECRET", "")


def _check_secret(x_vapi_secret: str | None):
    # Vapi lets you configure a custom header (server.secret) sent with every request.
    # Skipped only if no secret is configured at all (local dev convenience).
    if WEBHOOK_SECRET and x_vapi_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="invalid webhook secret")


def _tool_result(tool_call_id: str, result: dict) -> dict:
    return {"toolCallId": tool_call_id, "result": json.dumps(result)}


def _lookup_patient_by_phone(args: dict) -> dict:
    db = SessionLocal()
    try:
        phone = args.get("phone_number", "")
        digits = "".join(ch for ch in phone if ch.isdigit())[-10:]
        patient = crud.get_patient_by_phone(db, digits)
        if patient:
            return {
                "found": True,
                "patient_id": patient.patient_id,
                "first_name": patient.first_name,
                "last_name": patient.last_name,
            }
        return {"found": False}
    finally:
        db.close()


def _create_patient(args: dict) -> dict:
    db = SessionLocal()
    try:
        payload = schemas.PatientCreate(**args)
        patient = crud.create_patient(db, payload)
        logger.info("VAPI_CALL_CREATED_PATIENT payload=%s", args)
        return {
            "success": True,
            "patient_id": patient.patient_id,
            "message": f"Registered {patient.first_name} {patient.last_name}.",
        }
    except ValidationError as e:
        return {"success": False, "error": e.errors()}
    except Exception as e:
        logger.exception("VAPI create_patient DB write failed")
        return {"success": False, "error": f"database write failed: {e}"}
    finally:
        db.close()


def _update_patient(args: dict) -> dict:
    db = SessionLocal()
    try:
        patient_id = args.pop("patient_id", None)
        if not patient_id:
            return {"success": False, "error": "patient_id is required"}
        patient = crud.get_patient(db, patient_id)
        if not patient:
            return {"success": False, "error": "patient not found"}
        payload = schemas.PatientUpdate(**args)
        patient = crud.update_patient(db, patient, payload)
        logger.info("VAPI_CALL_UPDATED_PATIENT id=%s payload=%s", patient_id, args)
        return {"success": True, "patient_id": patient.patient_id}
    except ValidationError as e:
        return {"success": False, "error": e.errors()}
    except Exception as e:
        logger.exception("VAPI update_patient DB write failed")
        return {"success": False, "error": f"database write failed: {e}"}
    finally:
        db.close()


TOOL_DISPATCH = {
    "lookupPatientByPhone": _lookup_patient_by_phone,
    "createPatient": _create_patient,
    "updatePatient": _update_patient,
}


@router.post("/webhook")
async def vapi_webhook(request: Request, x_vapi_secret: str | None = Header(default=None)):
    _check_secret(x_vapi_secret)
    body = await request.json()
    message = body.get("message", {})
    msg_type = message.get("type")

    # Tool/function calls the assistant makes mid-conversation.
    if msg_type == "tool-calls":
        results = []
        for call in message.get("toolCalls", []):
            fn = call.get("function", {})
            name = fn.get("name")
            args = fn.get("arguments") or {}
            if isinstance(args, str):
                args = json.loads(args)
            handler = TOOL_DISPATCH.get(name)
            if not handler:
                results.append(_tool_result(call.get("id"), {"error": f"unknown tool {name}"}))
                continue
            result = handler(args)
            results.append(_tool_result(call.get("id"), result))
        return {"results": results}

    # End-of-call report: fulfills the "log agent conversations" observability requirement.
    if msg_type == "end-of-call-report":
        summary = message.get("summary")
        transcript = message.get("transcript")
        call_id = message.get("call", {}).get("id")
        logger.info(
            "CALL_ENDED call_id=%s summary=%s transcript_len=%s",
            call_id, summary, len(transcript or ""),
        )
        # Full transcript logged at debug volume so stdout stays readable.
        logger.debug("CALL_TRANSCRIPT call_id=%s transcript=%s", call_id, transcript)
        return {"received": True}

    # Anything else (status updates, speech-update events, etc.) - ack and ignore.
    return {"received": True}
