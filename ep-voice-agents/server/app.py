"""
Webhook server that receives post-call data from ElevenLabs.

Run with:
    uv run uvicorn server.app:app --reload --port 8000

For local development, expose via ngrok:
    ngrok http 8000

Then set the ngrok URL as your webhook in ElevenLabs agent settings.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="EP Voice Agents - Webhook Server")

# Store conversations locally for now (Phase 2: move to DB)
DATA_DIR = Path("data/conversations")
DATA_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/webhooks/elevenlabs/post-call")
async def handle_post_call(request: Request):
    """
    Receives post-call transcription webhook from ElevenLabs.

    Contains: full transcript, analysis results, extracted data, metadata.
    Docs: https://elevenlabs.io/docs/agents-platform/workflows/post-call-webhooks
    """
    payload = await request.json()

    conversation_id = payload.get("conversation_id", "unknown")
    agent_id = payload.get("agent_id", "unknown")

    logger.info(f"Received post-call webhook: conversation={conversation_id}, agent={agent_id}")

    # Save raw payload
    filepath = DATA_DIR / f"{conversation_id}.json"
    filepath.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    logger.info(f"Saved to {filepath}")

    # Extract key data points (these come from ElevenLabs data collection config)
    analysis = payload.get("analysis", {})
    data_collection = analysis.get("data_collection", {})
    evaluation = analysis.get("evaluation_criteria_results", {})

    if data_collection:
        logger.info(f"Extracted data: {json.dumps(data_collection, indent=2, ensure_ascii=False)}")

    if evaluation:
        logger.info(f"Evaluation results: {json.dumps(evaluation, indent=2, ensure_ascii=False)}")

    # Extract transcript summary
    transcript = payload.get("transcript", [])
    turn_count = len(transcript)
    logger.info(f"Transcript: {turn_count} turns")

    return {
        "status": "received",
        "conversation_id": conversation_id,
        "turns": turn_count,
        "data_extracted": list(data_collection.keys()) if data_collection else [],
    }


@app.post("/webhooks/elevenlabs/post-call-audio")
async def handle_post_call_audio(request: Request):
    """
    Receives post-call audio webhook (base64 MP3).
    Enable 'Send audio data' in ElevenLabs webhook settings if needed.
    """
    payload = await request.json()
    conversation_id = payload.get("conversation_id", "unknown")

    # Save audio if present
    audio_data = payload.get("audio", None)
    if audio_data:
        audio_path = DATA_DIR / f"{conversation_id}.mp3.b64"
        audio_path.write_text(audio_data)
        logger.info(f"Saved audio for {conversation_id}")

    return {"status": "received", "conversation_id": conversation_id}