"""
EP Voice Agents — FastAPI backend.

Handles:
  - ElevenLabs post-call webhooks (transcript + extracted data)
  - REST API for conversation history
  - Health check

Run:
    uv run uvicorn server.app:app --reload --port 8000

Expose for ElevenLabs webhooks:
    ngrok http 8000
"""

import base64
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from server.models import (
    ConversationSummary,
    HealthResponse,
    PostCallAudioPayload,
    PostCallPayload,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("server")

app = FastAPI(
    title="EP Voice Agents",
    version="0.1.0",
    description="Webhook receiver and API for EP Group voice agents",
)

# CORS — allow frontend (Vercel, localhost) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Lock down to specific domains in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Local file storage (Phase 2: PostgreSQL)
DATA_DIR = Path("data/conversations")
DATA_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR = Path("data/audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


# ── Health ──────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse()


# ── Webhooks ────────────────────────────────────────────────────────────

@app.post("/webhooks/elevenlabs/post-call")
async def handle_post_call(payload: PostCallPayload):
    """
    Receives post-call webhook from ElevenLabs after a conversation ends.
    Validates payload, saves raw JSON, logs extracted data.
    """
    cid = payload.conversation_id
    logger.info(f"Post-call webhook: conversation={cid}, agent={payload.agent_id}")

    # Save raw payload
    filepath = DATA_DIR / f"{cid}.json"
    save_data = {
        "conversation_id": cid,
        "agent_id": payload.agent_id,
        "status": payload.status,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "analysis": payload.analysis.model_dump(),
        "transcript": [t.model_dump() for t in payload.transcript],
        "metadata": payload.metadata,
    }
    filepath.write_text(json.dumps(save_data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Saved to {filepath}")

    # Log extracted data
    dc = payload.analysis.data_collection
    collected_keys = [k for k, v in dc.items() if v] if dc else []
    if collected_keys:
        logger.info(f"Data collected: {collected_keys}")

    # Log evaluation
    ev = payload.analysis.evaluation_criteria_results
    if ev:
        logger.info(f"Evaluation: {json.dumps(ev, ensure_ascii=False)}")

    turn_count = len(payload.transcript)
    logger.info(f"Transcript: {turn_count} turns")

    return {
        "status": "received",
        "conversation_id": cid,
        "turns": turn_count,
        "data_extracted": collected_keys,
    }


@app.post("/webhooks/elevenlabs/post-call-audio")
async def handle_post_call_audio(payload: PostCallAudioPayload):
    """
    Receives post-call audio (base64-encoded MP3).
    Decodes and saves as .mp3 file.
    """
    cid = payload.conversation_id
    logger.info(f"Audio webhook: conversation={cid}")

    if payload.audio:
        audio_bytes = base64.b64decode(payload.audio)
        audio_path = AUDIO_DIR / f"{cid}.mp3"
        audio_path.write_bytes(audio_bytes)
        logger.info(f"Saved audio: {audio_path} ({len(audio_bytes)} bytes)")
        return {"status": "received", "conversation_id": cid, "audio_size": len(audio_bytes)}

    return {"status": "received", "conversation_id": cid, "audio_size": 0}


# ── REST API ────────────────────────────────────────────────────────────

@app.get("/api/conversations", response_model=list[ConversationSummary])
async def list_conversations():
    """List all stored conversations, newest first."""
    conversations = []

    for filepath in sorted(DATA_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            analysis = data.get("analysis", {})
            dc = analysis.get("data_collection", {})
            ev = analysis.get("evaluation_criteria_results", {})

            conversations.append(ConversationSummary(
                conversation_id=data.get("conversation_id", filepath.stem),
                agent_id=data.get("agent_id", "unknown"),
                timestamp=data.get("received_at", filepath.stat().st_mtime.__str__()),
                turns=len(data.get("transcript", [])),
                data_collected=[k for k, v in dc.items() if v],
                screening_complete=ev.get("screening_complete", {}).get("result") if isinstance(ev.get("screening_complete"), dict) else ev.get("screening_complete"),
            ))
        except Exception as e:
            logger.warning(f"Skipping {filepath.name}: {e}")

    return conversations


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get full conversation data by ID."""
    filepath = DATA_DIR / f"{conversation_id}.json"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Conversation not found")

    return json.loads(filepath.read_text(encoding="utf-8"))


@app.get("/api/conversations/{conversation_id}/audio")
async def get_conversation_audio(conversation_id: str):
    """Stream conversation audio as MP3."""
    audio_path = AUDIO_DIR / f"{conversation_id}.mp3"
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")

    return Response(
        content=audio_path.read_bytes(),
        media_type="audio/mpeg",
        headers={"Content-Disposition": f"inline; filename={conversation_id}.mp3"},
    )
