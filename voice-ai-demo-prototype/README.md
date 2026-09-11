# Voice Intake Prototype (Demo)

A single self-contained HTML file — `demo.html` — that shows what the finished
voice registration flow looks and feels like, without needing a live phone
number, Vapi account, or backend running.

## How to view it

Just open `demo.html` in any browser (double-click it, or drag it into a
browser tab). No server, install, or internet connection required.

Click **"Start demo call"**. It plays a pre-scripted conversation between the
voice agent ("Ava") and a caller, in real time, while:
- a **patient intake card** fills in field-by-field as each piece of
  information is confirmed (name → DOB → sex → phone → address → insurance),
- a system note shows the moment the agent would call the
  `lookupPatientByPhone` tool to check for a returning caller,
- a correction mid-call (the caller misspeaks an insurance member ID and
  fixes it) is shown flowing through to the intake card,
- once the caller confirms everything and the "call" ends, the new patient
  is added to the **patient roster** table below, alongside two pre-existing
  mock patients — standing in for what `GET /patients` would return.

## What this is (and isn't)

This is a **mock-up**, not a functional build:
- The transcript is hard-coded and plays the same way every time — there's
  no actual speech, LLM call, or telephony involved.
- The roster table is hard-coded sample data, not a real database.

Its purpose is to make the conversational design and data flow tangible at a
glance — what a reviewer would actually experience calling the finished
system, and what the resulting patient record looks like — before investing
the time to stand up real infrastructure.

## How it maps to the real system

| In this demo | In the real system |
|---|---|
| Scripted transcript bubbles | Vapi (telephony + STT/TTS) streaming live audio, transcribed and spoken in real time |
| "Ava"'s scripted lines | Claude, following the system prompt in `vapi/system_prompt.md` |
| The intake card filling in | The `createPatient` / `updatePatient` tool calls hitting `app/vapi_webhook.py` |
| The "lookupPatientByPhone" note | The actual duplicate-caller-detection tool call |
| The patient roster table | The real dashboard at `/`, backed by `GET /patients` and SQLite |

The full working code for all of the right-hand column is in the main
project repository (`voice-ai-patient-registration.zip`).
