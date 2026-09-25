# Authentication Architecture & Security Guide

## 1. Overview

Nerdearla Live Subtitles implements a lightweight, stateless, single-operator authentication layer designed for zero-session horizontal scaling on Google Cloud Run.

```
                              Browser
                                 │
                   1. POST /auth/login (username/password)
                                 ▼
                     Cloud Run: FastAPI Backend
                                 │
             ┌───────────────────┴───────────────────┐
             │ Verify via Argon2id                   │ Sign Stateless JWT (HS256)
             ▼                                       ▼
    Secret Manager:                         Secret Manager:
 nerdearla-auth-password-hash             nerdearla-auth-jwt-secret
                                 │
                                 ▼
                        Issue Access Token (8h)
                                 │
                 ┌───────────────┴───────────────┐
                 │                               │
                 ▼                               ▼
       REST Endpoints (Bearer)          WebSocket (/ws/{session_id})
    Authorization: Bearer <JWT>         Frame 1: {"type":"auth","token":"<JWT>"}
                 │                               │
                 └───────────────┬───────────────┘
                                 ▼
                         Backend Validates
                                 ▼
                     Initialize Gemini Live API
```

---

## 2. Distinction: User Auth vs. Google ADC

| System Boundary | Target | Mechanism | Storage / Secret Location |
|---|---|---|---|
| **Operator App Auth** | Access application features | Stateless Bearer JWT | React memory only (never localStorage) |
| **Backend Password Storage** | Validate operator credentials | Argon2id hash | Secret Manager (`nerdearla-auth-password-hash`) |
| **JWT Signature Key** | Sign and verify JWTs | Symmetric HMAC-SHA256 | Secret Manager (`nerdearla-auth-jwt-secret`) |
| **Backend → Google Cloud** | Invoke Gemini Live & Models | Application Default Credentials (ADC) | Cloud Run dedicated Service Account |
| **Backend → Redis** | Shared session state & Rate limits | Direct TCP / VPC Network | Memorystore / Redis URL |

---

## 3. Cryptographic Standards

### 3.1 Password Hashing (Argon2id)
* **Algorithm**: Argon2id (`argon2-cffi`)
* **Parameters**: 64 MiB memory cost, 3 iterations, 4 parallelism threads.
* Passwords are never logged, never stored in plaintext, and never placed into container images or Git.
* A CLI utility (`backend/scripts/hash_password.py`) securely generates password hashes with terminal echo disabled.

### 3.2 Token Architecture (JWT)
* **Algorithm**: HMAC-SHA256 (`HS256`)
* **Lifespan**: 8 hours (28,800 seconds)
* **Token Storage**: Held exclusively in React memory state (`AuthContext`). Refreshing the browser requires re-authentication, preventing cross-site scripting (XSS) persistent token exfiltration.
* **Revocation**: Rotating `AUTH_JWT_SECRET` in Secret Manager immediately invalidates all active sessions globally without maintaining server-side revocation tables.

---

## 4. WebSocket Authentication Protocol

Browser WebSocket clients cannot set custom HTTP `Authorization` headers. Passing tokens via URL query parameters (`/ws/session?token=...`) is strictly prohibited to avoid token leaks in server logs, proxy access logs, and browser history.

### Strict Handshake Sequence:
1. `WS OPEN` $\rightarrow$ State transitions to `AUTHENTICATING`. Gemini Live is **not** started.
2. First message sent by client **must** be:
   ```json
   {
     "type": "auth",
     "token": "<JWT>"
   }
   ```
3. Backend validates JWT signature, subject, and expiration:
   * **If valid**: State transitions to `AUTHENTICATED`, emits `{"type": "auth_success"}`, and then initiates Gemini Live API (`GEMINI_CONNECTING` $\rightarrow$ `GEMINI_READY`).
   * **If invalid or expired**: Backend emits structured error (`AUTH_INVALID_TOKEN` or `AUTH_EXPIRED`), state transitions to `ERROR`, and closes WebSocket with code `1008`.
4. Any audio chunk, translation request, or control message sent prior to authentication is immediately rejected.
5. Reconnection with exponential backoff automatically re-transmits the in-memory token on every new socket instance.

---

## 5. Brute Force Protection (Rate Limiting)

* Login attempts to `POST /auth/login` are throttled using Redis (`AuthRateLimiter`).
* Rate limit: 5 failed attempts per IP/username window (default: 5 minutes).
* Exceeding the threshold returns HTTP 429 (`Too Many Requests`).
* Successful authentication automatically resets the failure counter.
* Rate limiter state is shared across all Cloud Run instances via Redis.

---

## 6. Single-Operator Model & Scalability

* This version explicitly supports **one logical operator identity** (`admin`).
* The system is fully horizontally scalable on Cloud Run because authentication is stateless and uses cryptographic JWT validation. Any Cloud Run instance can validate any token without inter-instance memory sharing or session affinity requirements.
