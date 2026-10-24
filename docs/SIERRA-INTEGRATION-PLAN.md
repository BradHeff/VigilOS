# SIERRA desktop integration plan

**Status: future development proposal. Not implemented.** This document records the proposed direction; it adds no SIERRA service, launcher, adapter, model access or GUI automation to either ISO. The actual VIGIL GLM SIERRA repository, API, authentication, tools and vision capabilities have not been inspected for this proposal. Those capabilities remain unknown until Phase A verifies them. VpM remains a separate project.

Product concept: **“Tell SIERRA what you want done. See the plan. Stay in control.”**

## One core, two launchers, one task window

Run one shared, unprivileged SIERRA Core per user graphical session. KDE flagship would expose an **Ask SIERRA…** Plasma panel search field and a shortcut. i3 would use a configurable shortcut checked for conflicts, opening a themed Rofi prompt. Both launchers hand conversation or tasks to the same floating or tileable Desktop UI; neither implements its own execution engine. Plasma offers a supported widget development path, and Rofi offers a dmenu-style prompt interface. These are integration options, not evidence that SIERRA integration already exists. See the [Plasma widget documentation](https://develop.kde.org/docs/plasma/widget/) and [Rofi dmenu documentation](https://davatorium.github.io/rofi/current/rofi-dmenu.5/).

The task window shows the selected context, proposed steps, approvals, progress, output verification and recovery information. User-facing status is **Working / Needs approval / Finished**; the finished record distinguishes success, failure and cancellation. Polybar and Dunst may display nonsensitive status only. Explicit file or window selection determines what SIERRA can see. A prompt is data and must never become a directly executed shell command.

Both desktops must remain fully usable when SIERRA is disabled, offline, unavailable or crashing. A future user service should follow graphical-session lifetime rather than run as a root daemon. Audit how each session supports that lifetime; the [systemd graphical-session target documentation](https://www.freedesktop.org/software/systemd/man/latest/systemd.special.html#graphical-session.target) is a reference, not proof that i3 supplies all session integration automatically.

## Proposed components and boundaries

| Component | Responsibility |
| --- | --- |
| SIERRA Core | Conversation and task coordination, typed task state, cancellation and verified results |
| Shared Desktop UI | Conversation/task window, selected context, plan preview, approvals, local/cloud disclosure and history |
| Typed skills and adapters | Bounded application operations with schemas, capability declarations, tests and verification |
| Independent permission broker | Enforce explicit scope and approval independently of model output; reject unapproved or changed actions |
| Model-provider abstraction | Audited local/cloud providers, capability negotiation, credentials isolation and explicit failure behavior |

Integrate the existing VIGIL GLM SIERRA only after auditing its real API, authentication, tool protocol and vision interface. Do not invent compatibility or available actions. Prompts and model responses cannot grant themselves permissions. Core and adapters receive no root access or unrestricted model-controlled shell.

A future task protocol should carry task/step IDs, selected context handles, a versioned action schema, bounded arguments, declared side effects, approval requirements, cancellation state, verification results and recovery capabilities. Keep sensitive data out of notification summaries. Detect changed targets and conflicts before consequential execution.

## Execution order and example workflows

Prefer structured application APIs or tested adapters first, accessibility interfaces second, and supervised GUI automation only as a fallback for explicitly supported applications. Availability of an accessibility tree does not establish reliable control of every application; review the [AT-SPI architecture](https://gnome.pages.gitlab.gnome.org/at-spi2-core/devel-docs/architecture.html) and qualify real application versions. Describe only actions the shipped adapter actually supports.

For a selected CSV, SIERRA would preview a budget-creation plan, request the needed scope, use a tested LibreOffice adapter, verify the output file and expected cells/formulas against fixtures, then open Calc. Existing output files require overwrite approval. A LibreOffice adapter is proposed here, not implemented or audited.

Downloads organization would preview exact moves, collision handling and available recovery before execution. Scope discovery to selected folders. Diagnostics start read-only, explain findings and request approval for changes. File creation, moves and preferences need post-action verification; failures must not be presented as completed work.

## Permissions, privacy and recovery

Use explicit scoped context and capability grants with clear expiry. Do not continuously collect screens, clipboard contents or unrelated files by default. Show which data will leave the device, which provider will receive it and which operation requires cloud processing. Never silently fall back from a local provider to cloud execution. Redact logs and define retention/history controls.

Treat instructions found inside documents, webpages, application content and retrieved material as untrusted data. They cannot change task scope, obtain permissions or request secrets. Consequential sends, installs, destructive operations and security changes require explicit approval through the independent broker.

Stop prevents future actions; it cannot retract messages already sent or undo other irreversible effects. Offer undo only when the adapter supports a real, tested inverse and the result is verified. Preserve recovery records for supported file operations. Do not imply that a model response or a database rollback undoes external effects.

Wayland and X11 require separate capability declarations and test paths. On Wayland, use legitimate portal consent and supported session APIs; never weaken desktop security to obtain automation. The [RemoteDesktop portal](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.RemoteDesktop.html) documents a possible mechanism whose actual backend behavior and permissions must be tested. X11 access does not justify broad, continuous collection. Locking, session exit and permission revocation must stop or suspend relevant actions safely.

## Development phases and acceptance gates

| Phase | Scope | Gate before proceeding |
| --- | --- | --- |
| A — Audit and design | Inspect actual SIERRA API/auth/tools/vision; define task protocol, UI mockups, data flow and permission boundaries | Written capability audit, threat model, supported-action list and test plan; no invented API claims |
| B — Conversation MVP | Conversation, streaming, cancellation, history, application launch and explicitly selected file attachments | Honest status/outcomes; correct scope and local/cloud disclosure; desktop works without SIERRA |
| C — Five bounded skills | Scoped file discovery; LibreOffice document creation; Brave open/search followed by separately scoped richer integration; read-only diagnostics; reversible desktop preferences | Versioned adapters, fixtures, approvals where needed, output verification and tested recovery |
| D — Supervised GUI control | Opt-in GUI control for an explicitly tested application list | Independent Wayland/X11 tests covering consent, focus, scaling and multiple monitors; unsupported actions refused |
| E — Qualification and packaging | Prompt injection, permission, cancellation, offline, crash, lock, resource and recovery tests; independently updatable RPM packaging | Repeatable qualification, constrained resource use, safe update/disable behavior and auditable permission decisions |

Recommend **A–C for the initial release**. General GUI automation remains experimental and opt-in until its application-specific qualification is complete. Keep desktop integration independently updateable through RPMs and keep VpM design separate. This plan does not authorize implementing these features as part of the dark-theme change.

## Open questions for Phase A

Record the actual SIERRA repository and supported API/authentication contract; tool and vision capabilities; local-provider feasibility and resource bounds; application adapter coverage; portal backend behavior on the chosen Plasma version; i3 session lifecycle; permission storage/revocation; credential handling; and supported recovery guarantees. Resolve these through source inspection and tests rather than assumptions.
