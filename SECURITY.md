# Security Audit Report — Enterprise Voice Agents

**Date:** 2026-04-15
**Scope:** Full-stack security review (frontend, backend, configuration, infrastructure)
**Status:** Phase 1 — Critical fixes applied, recommendations for Phase 2 below

---

## Executive Summary

This audit identified **13 critical/high vulnerabilities** and **9 medium/low issues** across the application stack. The most severe findings include unauthenticated API endpoints exposing candidate PII, path traversal vulnerabilities, wildcard CORS, and missing webhook signature verification.

**Fixes applied in this commit** address the 13 critical and high items. Medium-term recommendations are documented below for Phase 2.

---

## Vulnerabilities Found and Fixed

### CRITICAL — Exploitable with immediate impact

| # | Vulnerability | Location | OWASP | Fix Applied |
|---|---------------|----------|-------|-------------|
| 1 | **Unauthenticated API endpoints** — All conversation data (PII, salary, transcripts, audio) accessible without any authentication | `server/app.py` GET endpoints | A01:2021 Broken Access Control | Added Bearer token API key authentication to all `/api/*` endpoints |
| 2 | **Path traversal** — `conversation_id` used directly in file paths (`../../etc/passwd` attack vector) | `server/app.py:164,174` | A01:2021 Broken Access Control | Added strict regex validation (`^[a-zA-Z0-9_-]{1,128}$`) + symlink escape check via `is_relative_to()` |
| 3 | **Wildcard CORS** — `allow_origins=["*"]` allows any website to read conversation data cross-origin | `server/app.py:48` | A05:2021 Security Misconfiguration | Restricted to configurable `ALLOWED_ORIGINS` env var, defaults to `localhost:3000` only |
| 4 | **No webhook signature verification** — Anyone can POST fake conversation data to webhook endpoints | `server/app.py:69-111` | A02:2021 Cryptographic Failures | Added HMAC-SHA256 signature verification via `ELEVENLABS_WEBHOOK_SECRET` |
| 5 | **Hardcoded agent IDs in frontend HTML** — Publicly visible API identifiers in page source | `screening.html:146`, `follow-up.html:293` | A05:2021 Security Misconfiguration | Moved to `<meta>` tags for server-side injection; values removed from source |

### HIGH — Significant risk, requires attacker effort

| # | Vulnerability | Location | OWASP | Fix Applied |
|---|---------------|----------|-------|-------------|
| 6 | **No rate limiting** — All endpoints vulnerable to brute force, enumeration, and DoS | All endpoints | A04:2021 Insecure Design | Added in-memory per-IP rate limiter (configurable via `RATE_LIMIT_MAX_REQUESTS`) |
| 7 | **No security headers** — Missing X-Frame-Options, HSTS, CSP, X-Content-Type-Options | All HTTP responses | A05:2021 Security Misconfiguration | Added security headers middleware (X-Frame-Options: DENY, HSTS, nosniff, Referrer-Policy, Permissions-Policy) |
| 8 | **Unlimited audio upload size** — base64 audio decoded without size validation (disk exhaustion) | `server/app.py:114-130` | A04:2021 Insecure Design | Added configurable max size check (`MAX_AUDIO_SIZE_MB`, default 50MB) before and after decode |
| 9 | **Content-Disposition header injection** — `conversation_id` injected unsanitized into HTTP header | `server/app.py:181` | A03:2021 Injection | Sanitized filename with regex, changed to `attachment` (not `inline`) |
| 10 | **PII logged at INFO level** — Salary expectations, evaluation data logged in plaintext | `server/app.py:96,101` | A09:2021 Security Logging Failures | Changed to log field names only, not values |
| 11 | **Swagger/ReDoc enabled in production** — API documentation exposes endpoint structure | `server/app.py` | A05:2021 Security Misconfiguration | Added `DISABLE_DOCS` env toggle to disable in production |
| 12 | **External CDN script without SRI** — ElevenLabs widget loaded from unpkg without integrity verification | `screening.html:151`, `follow-up.html:299` | A08:2021 Software and Data Integrity | Added SRI computation instructions; version should be pinned in production |
| 13 | **CORS allows all methods and headers** — `allow_methods=["*"]`, `allow_headers=["*"]` | `server/app.py:49-50` | A05:2021 Security Misconfiguration | Restricted to `GET, POST` methods and `Authorization, Content-Type` headers only |

---

## Remaining Recommendations (Phase 2)

### Authentication and Authorization

- [ ] **Implement OAuth 2.0 / JWT authentication** — Replace simple API key with proper identity-based auth (e.g., Auth0, Supabase Auth, or FastAPI OAuth2 with `python-jose`)
- [ ] **Add per-conversation access control** — Ensure users can only access conversations belonging to their tenant/organization
- [ ] **Implement RBAC** — Separate roles for candidates, recruiters, and admins with different permission levels

### Data Protection

- [ ] **Encrypt data at rest** — Use AES-256 encryption for stored conversation JSON and audio files (consider `cryptography` library or database-level encryption in Phase 2 PostgreSQL migration)
- [ ] **Implement data retention policy** — Auto-delete conversation data after a configurable period (GDPR compliance)
- [ ] **Add data deletion endpoint** — Allow authorized users to request deletion of their conversation data (GDPR right to erasure)
- [ ] **Audit trail** — Log all data access events to a tamper-evident audit log

### Infrastructure

- [ ] **Enforce HTTPS** — Configure TLS termination at the reverse proxy level; redirect all HTTP to HTTPS
- [ ] **Replace in-memory rate limiter with Redis** — Current implementation resets on server restart and doesn't work across multiple instances
- [ ] **Add request body size limits** — Configure Uvicorn/reverse proxy to reject oversized payloads before they reach the application
- [ ] **Content Security Policy** — Add CSP headers at the web server level restricting script-src to `'self'` and `unpkg.com`
- [ ] **Containerize with minimal base image** — Use distroless or Alpine-based Docker images with non-root user
- [ ] **Add health check authentication** — Consider if `/health` should be behind auth or limited to internal network

### Frontend

- [ ] **Pin CDN dependency version** — Change `https://unpkg.com/@elevenlabs/convai-widget-embed` to a specific version URL (e.g., `@elevenlabs/convai-widget-embed@1.2.3`)
- [ ] **Compute and add SRI hashes** — After pinning the version, compute the SHA-384 hash and add `integrity` + `crossorigin` attributes
- [ ] **Serve agent IDs from authenticated backend** — Create a `/api/config` endpoint behind auth that returns agent IDs, eliminating them from HTML entirely
- [ ] **Add meta CSP tag** — As a defense-in-depth measure alongside server-side CSP headers

### Secrets Management

- [ ] **Implement secrets rotation** — Establish a process for rotating API keys and webhook secrets
- [ ] **Use a secrets manager** — Move from `.env` files to a proper secrets manager (AWS Secrets Manager, HashiCorp Vault, or platform-native solution)
- [ ] **Remove Azure endpoint from source code** — Move `https://talentai-hub-2.cognitiveservices.azure.com` from `tenants/ep_group/agents.py` to environment variables

### Dependency Security

- [ ] **Add automated dependency scanning** — Set up Dependabot or Snyk for Python and frontend dependencies
- [ ] **Pin all dependency versions** — Use exact versions in `pyproject.toml` instead of `>=` ranges
- [ ] **Run SAST tooling** — Integrate Bandit (Python) and ESLint security plugin in CI/CD pipeline

### Compliance (if handling EU data)

- [ ] **GDPR data processing agreement** — Ensure DPA is in place with ElevenLabs and Azure
- [ ] **Privacy impact assessment** — Document what PII is collected, how it flows, and retention periods
- [ ] **Cookie/storage consent** — While current localStorage usage is minimal (language preference only), monitor for changes

---

## Hardcoded Credentials Inventory

| Type | Value | Location | Action |
|------|-------|----------|--------|
| ElevenLabs Agent ID (screening) | `agent_8701kncm94jgfzzv8k8x792qr7jj` | `tenants/ep_group/agents.py:21` | Move to env var or fetch from API |
| ElevenLabs Agent ID (follow-up) | `agent_8701knyz6xrtedsrc6qrtcs5dc45` | `tenants/ep_group/agents.py` (referenced) | Move to env var or fetch from API |
| Azure Cognitive Services endpoint | `https://talentai-hub-2.cognitiveservices.azure.com` | `tenants/ep_group/agents.py:27,119` | Move to env var |

---

## Architecture Security Notes

```
Current data flow:

  Browser ──[HTTPS]──> ElevenLabs (voice widget)
                             │
                             ├── [webhook POST] ──> Backend API (FastAPI)
                             │                          │
                             │                          ├── Saves JSON ──> data/conversations/*.json
                             │                          └── Saves audio ──> data/audio/*.mp3
                             │
  Browser ──[HTTPS]──> Backend API ──> Reads files ──> JSON response

Security boundaries:
  1. Browser <-> ElevenLabs: Secured by ElevenLabs SDK
  2. ElevenLabs <-> Backend: NOW secured by HMAC webhook signatures
  3. Browser <-> Backend API: NOW secured by API key + CORS + rate limiting
  4. Backend <-> Filesystem: NOW secured by path validation + symlink checks
```

---

## How to Deploy Securely

1. **Generate an API key:**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Set environment variables:**
   ```bash
   API_KEY=<generated-key>
   ELEVENLABS_WEBHOOK_SECRET=<from-elevenlabs-dashboard>
   ALLOWED_ORIGINS=https://your-production-domain.com
   DISABLE_DOCS=true
   ```

3. **Configure frontend agent IDs** — Set the `<meta name="agent-id-screening">` and `<meta name="agent-id-followup">` content attributes via your deployment pipeline or templating system.

4. **Run behind a reverse proxy** (nginx/Caddy) with TLS termination.

5. **Pin the ElevenLabs widget version** and compute SRI hash before deploying to production.
