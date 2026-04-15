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
import hashlib
import hmac
import json
import logging
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from server.models import (
    ConversationSummary,
    HealthResponse,
    PostCallAudioPayload,
    PostCallPayload,
)

load_dotenv()

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
    docs_url=None if os.getenv("DISABLE_DOCS", "").lower() == "true" else "/docs",
    redoc_url=None if os.getenv("DISABLE_DOCS", "").lower() == "true" else "/redoc",
)

# ── Security configuration ─────────────────────────────────────────────

API_KEY = os.getenv("API_KEY", "")
WEBHOOK_SECRET = os.getenv("ELEVENLABS_WEBHOOK_SECRET", "")
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if o.strip()
]
MAX_AUDIO_SIZE_MB = int(os.getenv("MAX_AUDIO_SIZE_MB", "50"))
MAX_AUDIO_SIZE_BYTES = MAX_AUDIO_SIZE_MB * 1024 * 1024

# Rate limiter state (per-IP, in-memory — replace with Redis in production)
_rate_limit_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "60"))


# ── CORS — restrict to configured origins ──────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS else ["http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=False,
    max_age=600,
)


# ── Security middleware ────────────────────────────────────────────────

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), payment=()"
    )
    response.headers["Cache-Control"] = "no-store"
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    # Clean old entries
    _rate_limit_store[client_ip] = [
        t for t in _rate_limit_store[client_ip]
        if now - t < RATE_LIMIT_WINDOW
    ]

    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        return Response(
            content='{"detail":"Rate limit exceeded. Try again later."}',
            status_code=429,
            media_type="application/json",
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
        )

    _rate_limit_store[client_ip].append(now)
    return await call_next(request)


# ── Helpers ────────────────────────────────────────────────────────────

# Strict pattern: only alphanumeric, hyphens, and underscores allowed
_SAFE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")


def _validate_conversation_id(conversation_id: str) -> str:
    """Validate conversation ID to prevent path traversal and injection."""
    if not _SAFE_ID_PATTERN.match(conversation_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid conversation ID format",
        )
    return conversation_id


def _require_api_key(request: Request) -> None:
    """Validate API key from Authorization header."""
    if not API_KEY:
        logger.warning("API_KEY not configured — endpoint is unprotected")
        return

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization")

    token = auth_header[7:]
    if not hmac.compare_digest(token, API_KEY):
        raise HTTPException(status_code=403, detail="Invalid API key")


def _verify_webhook_signature(payload_body: bytes, signature: str) -> bool:
    """Verify ElevenLabs webhook signature using HMAC-SHA256."""
    if not WEBHOOK_SECRET:
        logger.warning("ELEVENLABS_WEBHOOK_SECRET not configured — webhook signature not verified")
        return True

    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


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
async def handle_post_call(request: Request, payload: PostCallPayload):
    """
    Receives post-call webhook from ElevenLabs after a conversation ends.
    Validates signature, validates payload, saves raw JSON.
    """
    # Verify webhook signature
    signature = request.headers.get("X-ElevenLabs-Signature", "")
    if WEBHOOK_SECRET and not signature:
        raise HTTPException(status_code=401, detail="Missing webhook signature")
    body = await request.body()
    if not _verify_webhook_signature(body, signature):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

    cid = _validate_conversation_id(payload.conversation_id)
    logger.info("Post-call webhook: conversation=%s, agent=%s", cid, payload.agent_id)

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
    logger.info("Saved conversation %s", cid)

    # Log collected field names only (no PII values)
    dc = payload.analysis.data_collection
    collected_keys = [k for k, v in dc.items() if v] if dc else []
    if collected_keys:
        logger.info("Fields collected: %s", collected_keys)

    turn_count = len(payload.transcript)
    logger.info("Transcript: %d turns", turn_count)

    return {
        "status": "received",
        "conversation_id": cid,
        "turns": turn_count,
        "data_extracted": collected_keys,
    }


@app.post("/webhooks/elevenlabs/post-call-audio")
async def handle_post_call_audio(request: Request, payload: PostCallAudioPayload):
    """
    Receives post-call audio (base64-encoded MP3).
    Verifies signature, validates size, decodes, and saves as .mp3 file.
    """
    # Verify webhook signature
    signature = request.headers.get("X-ElevenLabs-Signature", "")
    if WEBHOOK_SECRET and not signature:
        raise HTTPException(status_code=401, detail="Missing webhook signature")
    body = await request.body()
    if not _verify_webhook_signature(body, signature):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

    cid = _validate_conversation_id(payload.conversation_id)
    logger.info("Audio webhook: conversation=%s", cid)

    if payload.audio:
        # Validate base64 size before decoding (base64 is ~33% larger than raw)
        estimated_raw_size = len(payload.audio) * 3 // 4
        if estimated_raw_size > MAX_AUDIO_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Audio exceeds maximum size of {MAX_AUDIO_SIZE_MB}MB",
            )

        audio_bytes = base64.b64decode(payload.audio)
        if len(audio_bytes) > MAX_AUDIO_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Audio exceeds maximum size of {MAX_AUDIO_SIZE_MB}MB",
            )

        audio_path = AUDIO_DIR / f"{cid}.mp3"
        audio_path.write_bytes(audio_bytes)
        logger.info("Saved audio for conversation %s (%d bytes)", cid, len(audio_bytes))
        return {"status": "received", "conversation_id": cid, "audio_size": len(audio_bytes)}

    return {"status": "received", "conversation_id": cid, "audio_size": 0}


# ── REST API ────────────────────────────────────────────────────────────

@app.get("/api/conversations", response_model=list[ConversationSummary])
async def list_conversations(request: Request):
    """List all stored conversations, newest first. Requires API key."""
    _require_api_key(request)

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
            logger.warning("Skipping %s: %s", filepath.name, e)

    return conversations


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, request: Request):
    """Get full conversation data by ID. Requires API key."""
    _require_api_key(request)
    cid = _validate_conversation_id(conversation_id)

    filepath = DATA_DIR / f"{cid}.json"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Resolve to ensure no symlink escape
    if not filepath.resolve().is_relative_to(DATA_DIR.resolve()):
        raise HTTPException(status_code=403, detail="Access denied")

    return json.loads(filepath.read_text(encoding="utf-8"))


@app.get("/api/conversations/{conversation_id}/audio")
async def get_conversation_audio(conversation_id: str, request: Request):
    """Stream conversation audio as MP3. Requires API key."""
    _require_api_key(request)
    cid = _validate_conversation_id(conversation_id)

    audio_path = AUDIO_DIR / f"{cid}.mp3"
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")

    if not audio_path.resolve().is_relative_to(AUDIO_DIR.resolve()):
        raise HTTPException(status_code=403, detail="Access denied")

    # Safe Content-Disposition: strip any injection characters
    safe_filename = re.sub(r"[^a-zA-Z0-9_-]", "", cid) + ".mp3"

    return Response(
        content=audio_path.read_bytes(),
        media_type="audio/mpeg",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
    )
