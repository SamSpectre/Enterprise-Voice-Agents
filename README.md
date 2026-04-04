# Voice Agents

Configurable voice agent orchestration platform.
Voice agents handle conversations. Downstream agents process the output. Dashboards surface the insights.

Multi-tenant, multi-lingual, enterprise-ready. Built for the German market.

## Architecture

```
 User (candidate / client / employee)
          |
    [Call / Widget / Phone / WhatsApp]
          |
    ElevenLabs Conversational AI -----> Server Tools (real-time data)
    (STT + LLM + TTS)                         |
    LLM: Azure-hosted, per-tenant             |
          |                                   |
    Post-call Webhook                         |
          |                                   |
    FastAPI Backend <--------------------------+
          |
    PostgreSQL (conversations, tenants, extracted data)
          |
    LangGraph Processing (scoring, summaries, routing)
          |
    Integrations (HR4YOU, TalentAI, CRM, email, calendar)
          |
    Next.js Dashboard (conversation feed, metrics, management)
```

## Quick Start

```bash
uv init && uv add elevenlabs[pyaudio] python-dotenv fastapi uvicorn
cp .env.example .env  # fill in keys
uv run python scripts/talk.py  # talk to your agent
```

## Documentation

- [CLAUDE.md](CLAUDE.md) -- Project context and coding conventions
- [ROADMAP.md](ROADMAP.md) -- Phased development plan
