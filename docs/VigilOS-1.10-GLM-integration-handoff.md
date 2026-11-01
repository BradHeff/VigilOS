# VigilOS 1.10 / VIGIL Ask 0.3.1 production acceptance handoff

The owner requested that production sign-in remain a handoff. No real account is approved by this acceptance run. Local fake-server tests cannot prove the deployed server's approved-token shape, authenticated Bearer routes, credit settlement, history policy or refresh/revocation behaviour.

The earlier docs/VigilOS-AI-integration-plan.md describes the 0.2 cookie client and a historical server snapshot. Its claim that external-browser authorization is future work is superseded by the 0.3 client. Do not treat its historical server findings as a fresh review of the deployed device-flow implementation.

## Current client contract to verify on VIGIL GLM

This table is derived from the packaged 0.3.1 client, not an audit of deployed server code. First compare the deployed implementation against it; repair only confirmed server gaps in a separate VIGIL GLM change. Preserve the web and Code clients' existing behaviour.

| Route | Client expectation |
| --- | --- |
| `POST /api/desktop/device/authorize` | JSON `client_id: vigilos-ask`; HTTP 200 with `protocol_version: 1`, opaque `device_code`, `user_code` (4–32 letters/digits/hyphens), same-origin `verification_uri`, integer `expires_in` in 1–3600 seconds and polling `interval` in 1–60 seconds. |
| `POST /api/desktop/device/token` | `client_id`, device code and `grant_type: urn:ietf:params:oauth:grant-type:device_code`. Pending/slow-down/denied/expired errors are understood; success supplies access and refresh tokens, Bearer token type and expiry. |
| `POST /api/desktop/token/refresh` | `client_id: vigilos-ask`, `grant_type: refresh_token`, refresh token. Return a compatible rotated token pair; the client serializes refresh within a user account. |
| `GET /api/auth/me` | Bearer authentication; name/email either at the top level or under `user`. A nonempty email is required before saving a connection. |
| `GET /api/usage` | Bearer authentication; numeric `fiveHour.percent` and `week.percent`; an object in `capped` selects the cap notice. |
| `POST /api/chat` | Bearer authentication, JSON and SSE response. `model`, `thinkingEffort`, `messages`, and three false flags: `webSearch`, `imageTool`, `browserTool`. Defaults are `glm-5.3-flash` / `low`; choices include `glm-5.3`, `high`, `max`. |
| `POST /api/desktop/session/revoke` | Bearer authentication, empty JSON object; 200/204 or already-invalid 401 are accepted. |

Requests identify `x-vigil-desktop: ask` and `User-Agent: vigil-ask/0.3.1`. Treat these as telemetry, never authority. Bind privileges and account identity to the server-issued connection. Enforce a text-only Ask scope across every authenticated route, including alternate routes that accept desktop tokens. Rate-limit code creation and polling, expire and consume codes once, bind approval to the displayed device/account, hash stored refresh secrets and revoke the token family on proven reuse. Never return a web-session cookie as the desktop credential.

SSE must use `text/event-stream` and finish with `data: [DONE]`. Supported text events include OpenAI-style `choices[0].delta.content`, `type: content` plus `text`, and `replace_content`. Error strings or `error.message` terminate as failures. Reasoning marks a thinking state without displaying private reasoning. An `x-vigil-cap` response header shows the downgrade notice. Verify completion is emitted after the server has settled accounting; a closed stream without the terminator is a failed partial answer.

Do not make a privacy promise from a client flag. Confirm storage, web-history inclusion, operational logs and upstream retention in the deployed service, then align policy and the Ask disclosure. Check cancelled requests cannot continue unbounded work after disconnect. Use redacted request IDs and before/after usage figures as evidence, never credentials or raw prompts from other accounts.

## Delivery order for the GLM owner

1. Record the deployed revision and compare the route/token contract above. Use staging and a dedicated test account for failures and expiry cases.
2. Close any confirmed authentication, scope, billing, cancellation or retention gaps; add server regression checks with web/Code positive controls. Do not widen the desktop scope to make a test pass.
3. Run the owner acceptance sequence below on the exact installed 1.10 image. Record revision, ISO hash, result and redacted evidence for each item.
4. Publish account/privacy claims only after their checks pass. Keep any failed or untested item visible as a release limitation.

## Owner acceptance on an exact installed 1.10 image

1. Use a dedicated VIGIL GLM test account. Keep its password, device code and tokens out of chat, public screenshots and logs. Open VIGIL Ask, accept its disclosure, and choose Sign in. The ordinary browser should open https://chat.vigilglm.ai/desktop/verify. Sign in there, enter the code shown in Ask, and approve the named desktop. The UI must identify the intended account.
2. Ask one minimal question, then one follow-up. Verify streamed text, completed state and correct conversation context. Record pre/post account usage without recording credentials. The same account's plan limits and credits must apply; usage should reflect settled charges after completion.
3. Start another response and press Stop. Verify the stream closes promptly and server-side work is cancelled or honestly accounted for. Repeat cancellation on desktop lock and session exit. Stopped or failed partial answers must not appear completed.
4. Keep the connection until its real access token becomes due for refresh. Exercise the window and a terminal request together. Confirm refresh rotation works without reuse revocation, and the returned tokens and authenticated identity remain compatible. Use a test-server short expiry if supported; do not edit or expose production tokens to manufacture evidence.
5. Sign out in Ask, then verify the desktop is revoked in Settings → Accounts → Connected desktops. A request using that revoked connection must fail. Reconnect and test revocation from the account page; Ask must return to sign-in and preserve an unsent question/attachments.
6. If supported on the account, test Google and GitHub in the external browser. Confirm denied/expired codes, an already-used code and account changes fail safely. Never approve a code from an unrelated device.

## Server evidence to attach

Record deployed revision and protocol version; successful device authorization/polling, approved access/refresh token contract, Bearer /api/auth/me, /api/usage and /api/chat, rotation/reuse detection and revocation results. The caller-controlled x-vigil-desktop: ask header must not grant access by itself.

Confirm server-enforced Ask restrictions independently of the three false tool flags: no URL prefetch, execution tools, agents, Studio/project mode or unexpected account-memory injection. Test with positive web/Code controls so globally disabled fixtures cannot produce a false pass. Confirm Ask usage attribution, shared limits, the final stream terminator after settlement, and actual logging/history/provider retention before publishing privacy claims.

This is a production handoff, not a completed test or a request to modify VIGIL GLM during ISO acceptance.
