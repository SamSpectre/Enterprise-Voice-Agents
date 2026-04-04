# EP Voice Agents

Voice-powered AI agents for EP Group (Engineering People GmbH).
Built on ElevenLabs Conversational AI with Claude Sonnet 4.

## Quick Start

```bash
# 1. Create venv and install deps
uv init
uv add elevenlabs[pyaudio] python-dotenv fastapi uvicorn

# 2. Copy .env.example to .env and fill in your keys
cp .env.example .env

# 3. Test your agent via terminal conversation
uv run python scripts/talk.py

# 4. Run the webhook server (receives post-call data)
uv run uvicorn server.app:app --reload --port 8000
```

## Architecture

Phase 1 (current): ElevenLabs agent + webhook backend
Phase 2: Dashboard consuming webhook data
Phase 3: Multi-agent with LangGraph downstream processing
Phase 4: Multi-tenant deployment for client SMEs