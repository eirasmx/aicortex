# 🔒 Security Policy

## Supported Versions

Only the current stable release receives security fixes:

| Version | Status |
|---|---|
| 1.0.x | ✅ Supported — security fixes provided |
| < 1.0 | ❌ Unsupported — no fixes will be issued |

If you are on an older version, upgrade to 1.0.x before reporting.

---

## 🚨 Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Public disclosure before a fix is available puts all users at risk. Instead:

### How to Report

1. **Email** — send a report to **eirasmx@pm.me**
2. **Subject line** — use `[SECURITY] AI Cortex — brief description`
3. **Encrypt if possible** — PGP key available on request
4. **Allow time to respond** — see the timeline below before going public

### What to Include

A useful report contains:

- **Description** — what the vulnerability is and where it exists
- **Steps to reproduce** — minimal code or commands that trigger it
- **Impact assessment** — what an attacker could achieve by exploiting it
- **Affected versions** — which versions are vulnerable
- **Suggested fix** — if you have one (not required)

### Response Timeline

| Milestone | Target |
|---|---|
| Initial acknowledgment | Within 48 hours |
| Vulnerability confirmed or rejected | Within 7 days |
| Fix developed and tested | Within 30 days for critical issues |
| Coordinated public disclosure | After fix is deployed |

We will keep you informed at each stage. If you do not hear back within 48 hours, follow up by opening a GitHub issue with the subject `Security contact request` (no vulnerability details) so we know to check email.

---

## 🛡️ Security Architecture

### What AI Cortex Does

AI Cortex acts as a client library and API proxy for Ollama servers. It:
- Sends prompts over HTTP to local or remote Ollama instances
- Reads and writes model metadata JSON files on disk
- Optionally exposes an OpenAI-compatible HTTP server via FastAPI

### Threat Model

| Component | Risk | Mitigation |
|---|---|---|
| HTTP to Ollama | Traffic readable on network | Use HTTPS for remote servers; localhost traffic is lower risk |
| Model output | Unfiltered LLM output | Content filtering is the application's responsibility |
| Server mode | Unauthenticated API exposure | Do not expose on public networks without a reverse proxy that adds auth |
| Model metadata files | Tampered JSON could poison model lists | Files are bundled in the package and only modified by the tools pipeline |
| Input prompts | Prompt injection | Validate and sanitize user-supplied content before passing to `chat()` |

### What AI Cortex Does NOT Do

- Store or transmit API keys, credentials, or user data
- Log prompt content or model responses (at any log level)
- Make network connections outside of explicitly configured Ollama server URLs
- Execute arbitrary code from model responses

---

## 🔐 Security Best Practices for Users

### Network

- **Use HTTPS** when connecting to remote Ollama servers: `get_server_info(model, "https://your-server.example.com")`
- **Restrict server access** — Ollama should only be reachable from trusted hosts
- **Do not expose the built-in server** (`aicortex-server`) on a public interface without a reverse proxy (nginx, Caddy, etc.) that adds authentication and TLS termination

### Input Validation

- **Sanitize user input** before passing it to `chat()` — AI Cortex does not filter prompts
- **Validate model names** from untrusted sources against `models()` before use to prevent unexpected model selection

### Dependencies

- **Keep AI Cortex updated** — `pip install --upgrade aicortex-core`
- **Audit your dependency tree** — use `pip-audit` to check for known vulnerabilities in installed packages:
  ```bash
  pip install pip-audit
  pip-audit
  ```

### Server Mode

- **Add authentication** via a reverse proxy — the built-in server has no auth layer
- **Set `ALLOWED_ORIGINS`** if exposing via HTTP to control CORS
- **Rate-limit requests** at the proxy layer to prevent abuse

---

## 📋 Known Security Limitations

These are documented limitations, not bugs. They reflect intentional design trade-offs:

1. **No built-in authentication** — the server mode exposes endpoints without credentials. This is intentional for simplicity in local use; production deployments must add auth at the proxy layer.

2. **HTTP default for localhost** — connections to `http://localhost:11434` use plain HTTP. This is intentional; encrypting loopback traffic adds complexity with no real security benefit.

3. **Unfiltered model output** — AI Cortex does not inspect, filter, or modify model responses. Applications that display LLM output to end users are responsible for appropriate content handling.

4. **No rate limiting** — neither the library nor the server has built-in rate limiting. Add this at the infrastructure layer for production use.

---

## 🙏 Responsible Disclosure

We appreciate researchers who report vulnerabilities responsibly. In return, we commit to:

- Acknowledge your report promptly
- Keep you informed of progress
- Credit you in the security advisory (unless you prefer anonymity)
- Not pursue legal action against good-faith security research

Please do not:
- Access or exfiltrate user data beyond what is needed to demonstrate the vulnerability
- Perform denial-of-service testing
- Disclose publicly before we have shipped a fix
