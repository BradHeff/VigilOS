# VigilOS AI integration plan for VIGIL GLM

Prepared 1 November 2026 for the VIGIL Ask 0.2.0 client in VigilOS. This document is a server implementation and acceptance handoff, not evidence that production supports every contract below. No VIGIL GLM server changes were made in the VigilOS review. At the owner's request, production sign-in and a real charged question remain a handoff; automated stand-in and account-free checks do not close that release gate.

## Outcome and boundaries

Target behaviour: a VigilOS user signs into their VIGIL GLM account, asks a question in VIGIL Ask, receives a streamed answer and sees usage against that same account. No manually created API key is required. Requests consume the authenticated account's credits under the existing plan rules. Ask has no execution tools, browsing or image generation. SIERRA and desktop automation are outside this integration.

There are two stages:

1. Enforce the Ask-specific server policy below, then qualify the current session-cookie client using email sign-in and release only after real-account acceptance.
2. Add supported external-browser authorization and revocable desktop sessions; update the VigilOS client to consume that new protocol. This is required for reliable Google sign-in. These future endpoints do not exist in the current client.

The connected GitHub repository was inspected read-only at `BradHeff/VIGIL-GLM` commit `4c2dd877f54d349b2c866bc8c65282586a7b20b2`. The deployed revision was not established. Compare production with this snapshot before implementation; repository evidence is not a signed-in production test. No server files, settings or deployment were changed.

## Confirmed server gaps and concrete changes

The current client should **not be qualified for production until an Ask-specific server policy is enforced**. Changing the header to `code` would misclassify the client and still would not close every path below.

| Finding in the reviewed source | Required VIGIL GLM change | Acceptance evidence |
| --- | --- | --- |
| `src/app/api/chat/route.ts:216` recognizes only `code`; `ask` follows ordinary web branches | Define a validated client classification and a single Ask policy after normal session authorization. Retain `x-vigil-desktop: ask` as metadata only; future scoped desktop tokens should bind that identity | Valid Ask sessions work; missing, forged, revoked and banned sessions fail; a forged header grants no access |
| `chatToolPermissions.ts` honors the three false flags, but `route.ts:340` can still enable Code Mode and `:782` can start web agents | For Ask, disable **all** function tools, Code Mode, Studio/document completion, agent delegation and privileged command dispatch. Reject `clientTools`, `officeInputKeys`, project context and incompatible mode requests instead of silently enabling them | Prompts requesting a website, resume, file, agent team, audit or self-healing operation cause no tool, broker, agent or admin operation and no tool surcharge |
| `route.ts:527-529` extracts and fetches URLs independently of the three tool flags | Skip URL extraction/fetching for Ask. Attached URLs remain plain text unless a future explicit capability is designed | A controlled public URL in a question or attachment receives zero requests; no page text is injected |
| `route.ts:427-428` injects account memories and response preferences for non-Code clients | Decide the Ask privacy policy explicitly. Recommended initial policy: only the submitted conversation/attachments plus normal server safety policy; no web project/account-memory injection | Seed recognizable account/project memories; assert they are absent from the upstream Ask messages |
| Billing at `route.ts:1237` records Ask as `web`; `usageWindows.ts:275-287` knows only web/code/voice/api/other buckets | Add an `ask` surface through the billing types, transaction metadata, usage aggregation and account usage UI while reusing the existing account pool and limits | One Ask charge is attributed to Ask and reflected in the same five-hour/weekly totals; web and Code totals still reconcile |
| `route.ts:724-726` forwards upstream `[DONE]` before the `finally` settlement at `:1228`; Ask treats `[DONE]` as completion and closes | For Ask, suppress intermediate terminators and emit one final `[DONE]` only after successful post-processing and billing settlement. On failure send a safe error and close. Keep existing clients compatible | Delayed settlement cannot race the immediate usage refresh; no successful terminator precedes an error, replacement or additional content |
| Account/usage endpoints and both cookie names match the current client; the production cookie is `__Host-vigil_session`, HttpOnly/Secure, SameSite=Lax, Path=/, seven-day lifetime | Preserve `getServerSessionWithUser` / `getServerSession` checks for live session rows, bans and token versions. Explicitly test `ask` in middleware without widening the web CSRF policy | Email sign-in, revoked sessions, cross-origin refusals, and usage response shape pass on the deployed revision |

The middleware's `code` branch is a CSRF exception, not the only route into chat: an originless Ask request currently follows the ordinary branch. Do not report that `ask` is categorically rejected. The confirmed problem is its missing dedicated policy/classification. [Middleware source](https://github.com/BradHeff/VIGIL-GLM/blob/4c2dd877f54d349b2c866bc8c65282586a7b20b2/src/middleware.ts#L30), [chat route](https://github.com/BradHeff/VIGIL-GLM/blob/4c2dd877f54d349b2c866bc8c65282586a7b20b2/src/app/api/chat/route.ts#L208).

History is narrower than the original uncertainty: this client sends no `conversationId` and does not call conversation-write routes. The reviewed chat route's emergency save requires a conversation ID (`route.ts:1251`), so that path does not save these Ask turns. This is source evidence about that path, **not a general retention guarantee**; confirm logging, provider retention, account-memory handling and other persistence against production before publishing a promise.

For Ask attribution, also update `src/app/api/admin/usage/route.ts` (its surface allowlist), `src/components/chat/UsageMeter.tsx` (types and displayed surface list), and usage fixtures/tests such as `tests/usage-page.test.tsx`. Keep aggregate totals backward compatible for clients that ignore the new bucket.

Extend the existing `tests/integration/free-chat-api.test.ts`, `tests/integration/backend-route-auth.test.ts` and `tests/auth-core-session-revocation.test.ts`, and add a focused Ask policy test. Mock the model, tools, URL fetcher, agents, storage and billing sink so the negative assertions prove that no prohibited subsystem is invoked. Run a positive web/Code control alongside each negative Ask test; a broken mock or globally disabled tool must not appear as a successful isolation test.


## Current client contract: implement or explicitly confirm

Origin is exactly `https://chat.vigilglm.ai`. Python requests use TLS verification and do not follow redirects. A development override permits only loopback; a session saved for one origin is not loaded for another. Production must not redirect authenticated API calls to another host.

| Request | Current client expectation | Server work / acceptance |
| --- | --- | --- |
| Web view `GET /login` | Own-site email login and registration, ending at `/chat` or a child path | Confirm login, MFA if required, signup and expired-session flows; avoid redirecting the completed login elsewhere |
| Session cookie | `__Host-vigil_session` preferred; `vigil_session` also understood, scoped to chat.vigilglm.ai | Confirm actual name, host/path, Secure, HttpOnly, SameSite and expiration; never put a session in a URL |
| `GET /api/auth/me` | 200 JSON with top-level `email`/`name`, or a `user` object with those fields; 401 for invalid/revoked session | Return authenticated identity only. Use a stable account ID in the future desktop contract |
| `GET /api/usage` | 200 JSON with `fiveHour.percent`, `week.percent`; optional `capped` object | Confirm percentages, windows, reset behaviour and account consistency. Client displays these numbers; it does not enforce budgets |
| `POST /api/chat` | Session cookie, `x-vigil-desktop: ask`, `Accept: text/event-stream`, `Content-Type: application/json`, `User-Agent: vigil-ask/0.2.0` | Explicitly accept `ask` in desktop-client classification, while preserving auth, plan enforcement and web CSRF protections |
| Usage cap response | Optional `x-vigil-cap` response header | Current UI interprets presence as Flash/Low fallback. Send it only when that fallback actually applies |
| Unauthorized response | HTTP 401, JSON `{"error":"message"}` | Clear only the failed session locally. Do not return 401 for insufficient credits, rate limits or upstream failures |
| Other refusal | Non-200, preferably JSON `{"error":"safe user-facing message"}` | Use separate 402/403/429/5xx meanings. Avoid stack traces, secrets and prompts in error bodies |

`x-vigil-desktop` is caller-controlled metadata, **not authentication**. Do not grant extra credit, bypass plans or disable origin/CSRF checks merely because it says `ask` or `code`. Inspect how the existing desktop route protects requests that carry cookies without a browser Origin header. Preserve the web route's protections; if necessary create an authenticated desktop route with scoped tokens instead of a header-based exception.

Current request body (selected user settings may change model and effort):

```json
{
  "model": "glm-5.3-flash",
  "thinkingEffort": "low",
  "messages": [
    {"role": "user", "content": "VIGIL Ask instructions"},
    {"role": "assistant", "content": "Understood. I will answer here, without tools."},
    {"role": "user", "content": "The question and explicitly attached text"}
  ],
  "webSearch": false,
  "imageTool": false,
  "browserTool": false
}
```

Models currently allowed by the client: `glm-5.3-flash`, `glm-5.3`. Efforts: `low`, `high`, `max`. Defaults: Flash/Low. Confirm these identifiers against production configuration. Reject unsupported selections with a clear error or document an intentional server fallback. Enforce tools off for the Ask capability on the server as well as accepting the request booleans. No MCP, command execution or file-access capability should be attached to this client.

The instruction exchange above is not a privileged system message. Treat all incoming messages as untrusted. Server policy and tool restrictions must remain authoritative.

Follow-ups send the preceding successful turns and the new question in each request. There is no conversation ID or server-side resume protocol. Attached text is included in the user message. The client bounds the messages JSON to 1 MB and an individual attached file to 512 KiB; allow JSON envelope overhead or return a clear 413. Define and enforce model token limits on the server too.

## Streaming and cancellation

Respond with HTTP 200 and `Content-Type: text/event-stream`; disable reverse-proxy buffering. Emit UTF-8 `data:` lines terminated by a blank line. The current client expects one complete JSON value per data line, not a JSON object split across several SSE data fields.

Supported frames:

```text
data: {"choices":[{"delta":{"reasoning_content":"thinking text"}}]}

data: {"choices":[{"delta":{"content":"answer text"}}]}

data: {"replace_content":"replacement answer"}

data: {"error":"Safe error message"}

data: [DONE]

```

The client also understands `{"type":"thinking","text":"..."}`, `{"type":"content","text":"..."}` and top-level string `content`. Thinking text is not shown or persisted; it changes the status label. Usage frames are ignored by the answer renderer. Keep individual lines below 1 MiB and visible answers below two million characters.

`[DONE]` is required for success. EOF with partial text is a failed answer, and a stream error remains failure even if text already arrived. Emit an error on provider failure; never manufacture a success terminator after an incomplete response. Keep-alive comments should arrive inside the 120-second read timeout.

Stop, screen lock, window close, sign-out and session exit must terminate the request. Propagate downstream disconnects to the upstream model request and settle usage exactly once, including cancellation and provider errors. Cancelling cannot undo text already sent or credits already incurred; document the billing rule precisely. Avoid automatic retries of a chargeable POST without an idempotency protocol.

## Credits, limits and privacy decisions

Reuse the existing account budget implementation rather than creating a separate Ask credit pool. Identify the user from the validated session, authorize the chosen model, reserve or limit concurrency atomically, and record actual usage once. Test concurrent requests from web, Code and Ask against the same five-hour and weekly budgets. Make `/api/usage` reflect the same settled accounting.

Before release, decide and test whether Ask conversations enter web chat history. Recommendation: keep them out by default, consistent with the current no-conversation-ID client, while retaining the minimal accounting/audit data needed to operate the service. Verify this recommendation against actual product policy before implementation. The current client makes no promise about server history retention.

Document separately: local Ask history; server chat history; request/log retention; model-provider handling; deletion; and credit records. Never log Cookie headers, access tokens, login codes or full prompt/attachment contents by default. Screenshots and acceptance reports must use synthetic questions and hide account details.

The current client stores the reusable session in a mode-0600 file under a private state directory. It is not encrypted or keyring-backed. Sign out removes that local session and stops the active answer; it is not server revocation and does not clear local question history. Keep these distinctions in the UI and policy. A stolen web session currently has the account permissions of that session; scoped desktop credentials reduce this exposure.

## External-browser sign-in: server work required

Google prohibits embedded OAuth user agents. Removing `QtWebEngine` from a user agent does not create a supported flow. The reviewed client retains its true user agent and blocks Google authentication inside the web view with an explanation. Email remains the temporary path; GitHub needs real-account qualification too.

Implement a desktop authorization flow in the system browser. A device authorization flow is a suitable Linux desktop option because it needs no inbound listener or copying of browser cookies. Reuse an existing standards-based server implementation if present. Proposed names below are **new server endpoints**, not current APIs:

1. `POST /api/desktop/device/authorize`: accept a public client identifier `vigilos-ask`, return a high-entropy opaque device code, a short user code, an allowlisted HTTPS verification URI, expiration and polling interval. Store only hashed codes; rate-limit creation and code attempts.
2. System-browser verification: authenticate with email, Google or GitHub through the normal browser session. Show “Connect VIGIL Ask” with account and requested permissions. Require explicit confirmation; prevent login-CSRF, code substitution and accidental authorization of another device. A public client ID conveys no trust by itself.
3. `POST /api/desktop/device/token`: exchange/poll the device code using standard pending, slow-down, denial and expiration responses. Codes are short lived and single use; do not return a token before account approval. Do not log request bodies.
4. Issue a short-lived access token and rotating refresh token restricted to Ask chat, identity and usage. Bind audience and client classification server-side, validate scope on every route, detect refresh-token reuse and support revocation. Do not ship a client secret in the ISO.
5. `POST /api/desktop/token/refresh` and `POST /api/desktop/session/revoke`: authenticate appropriately, rotate safely and revoke only that desktop session. Expose devices and revoke controls in account settings.
6. VIGIL Ask follow-up patch: open the verification URI in the default browser, show the code, poll with cancellation, store credentials privately (prefer the desktop keyring with a documented fallback), refresh and revoke. Migrate existing cookie sessions by requiring fresh desktop authorization; never silently exchange broad credentials for broader access.

An authorization-code flow with PKCE and a loopback callback is an alternative if the server already implements it. In that case use an ephemeral loopback listener, exact redirect validation, state and S256 PKCE, a single-use code and a browser-visible completion page. Never return a web session cookie in a callback URL. Pick one flow and version its documented schema before implementing the client half.

Preserve VIGIL-Code compatibility during rollout. Do not silently change its cookie or chat response contract when adding Ask. Tests must cover existing web and Code clients as well as the new desktop route.

## Implementation order and release gates

| Step | Owner | Evidence required |
| --- | --- | --- |
| Reconcile reviewed snapshot with deployment | VIGIL GLM | Deployed revision and any differences from `4c2dd877` recorded |
| Enforce Ask policy and stream completion | VIGIL GLM | All confirmed gaps above covered by tests before a real Ask question |
| Qualify current email flow | VIGIL GLM + VigilOS | Dedicated free and paid test accounts complete a real answer, follow-up, stop, expiry and sign-out on both ISO editions |
| Close server compatibility gaps | VIGIL GLM | Integration tests for headers, identity, limits, tools-off, complete/error SSE and disconnect accounting; web/Code regressions pass |
| Implement browser authorization | VIGIL GLM | Device flow or PKCE endpoints, revocation and adversarial tests pass; schemas published |
| Implement desktop flow in Ask | VigilOS | Supported browser login, refresh, cancellation, private persistence and revocation tested on KDE and i3 |
| Release | Both | Exact ISO hashes, client/server versions, test-account results and remaining limitations recorded |

Use a dedicated test account and a stated credit budget. Start with a harmless prompt such as “Reply with VIGIL ASK TEST OK.” Keep credentials out of this repository, terminal arguments, logs and screenshots. The owner should complete interactive authentication. Do not use fake-server success as proof of production charging or privacy.

Real-account acceptance checklist:

- Email login; Google and GitHub only after the supported handoff exists; MFA, failed login, cancelled login and registration as applicable.
- Identity and usage correspond to the account that approved the desktop, including switching accounts.
- Flash/Low answer and a follow-up stream to completion; optional model/effort selections obey plan entitlement.
- Insufficient credits, cap fallback, rate limiting, upstream failure, malformed/truncated stream and offline recovery are clear and do not create false completed history.
- Stop, lock, logout and sign-out disconnect upstream work; accounting records show the expected one-time settlement.
- Expired/revoked sessions return to sign-in with the pending question and attachments intact. Late responses cannot restore an abandoned session or erase a newer sign-in.
- Ask chat history behaviour matches the published policy; logs contain no session tokens or attachment bodies.
- Both current web clients and VIGIL-Code remain functional.

## Sources

- [Google OAuth 2.0 policies: secure browsers](https://developers.google.com/identity/protocols/oauth2/policies): embedded OAuth is not supported.
- [Qt WebEngine profile documentation](https://doc.qt.io/qtforpython-6.11/PySide6/QtWebEngineCore/QWebEngineProfile.html): unnamed profiles are off the record; the application separately persists the chosen session.
- [OAuth for native apps (RFC 8252)](https://www.rfc-editor.org/rfc/rfc8252) and [device authorization (RFC 8628)](https://www.rfc-editor.org/rfc/rfc8628): reference contracts for the future browser handoff.
- Current client: `vigil-ask/vigil_ask/vigil_glm.py`, `signin.py`, `window.py` and `cli.py`. These files define the current compatibility contract; proposed endpoints above remain future work.

Read-only server references at the reviewed commit: [session validation and cookies](https://github.com/BradHeff/VIGIL-GLM/blob/4c2dd877f54d349b2c866bc8c65282586a7b20b2/src/lib/auth.ts), [identity response](https://github.com/BradHeff/VIGIL-GLM/blob/4c2dd877f54d349b2c866bc8c65282586a7b20b2/src/app/api/auth/me/route.ts), [usage route](https://github.com/BradHeff/VIGIL-GLM/blob/4c2dd877f54d349b2c866bc8c65282586a7b20b2/src/app/api/usage/route.ts), [usage aggregation](https://github.com/BradHeff/VIGIL-GLM/blob/4c2dd877f54d349b2c866bc8c65282586a7b20b2/src/lib/usageWindows.ts), [tool flags](https://github.com/BradHeff/VIGIL-GLM/blob/4c2dd877f54d349b2c866bc8c65282586a7b20b2/src/lib/chatToolPermissions.ts). These private source links are for the owner's implementation handoff.
