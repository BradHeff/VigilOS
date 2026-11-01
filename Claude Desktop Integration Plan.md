# VIGIL OS: Claude Desktop Integration Plan

Oct 31, 2026 · @Brad

## Summary

Ubuntu itself didn't build Claude into its desktop. What people are using on Ubuntu is Anthropic's official [Claude Desktop for Linux](https://code.claude.com/docs/en/desktop-linux), which went into beta on 30 June 2026 for Ubuntu 22.04+ and Debian 12+ from Anthropic's own apt repo. It brings Chat, Cowork and Claude Code into one app, plus a tray icon and a Quick Entry hotkey.

Canonical's own AI work is a separate track. It's opt-in, mostly local models delivered as snaps, and the first piece (Myna, a speech-to-text agent) landed in Ubuntu 26.10 on 15 October 2026.

The catch for us: the desktop app is Debian-only, and Anthropic lists Fedora and RHEL as not supported yet. The piece that does work on Fedora 44 is the Claude Code CLI, which has an official signed dnf repo.

Recommendation: build a thin integration of our own, called VIGIL Ask, on top of the Claude Code CLI. That means a KRunner prompt and shortcut on Plasma, a Rofi prompt and Polybar status on i3, and one shared answer window for both. Ship the integration and the repo definition by default, keep the Claude Code binary an opt-in install until the redistribution terms are checked, and build it as the first provider behind the SIERRA launcher design already in AI.md so none of it gets thrown away later.

## What the research found

There are four separate things that get lumped together as "Claude on Ubuntu".

| Piece | Who makes it | Linux support | What it gives you |
| --- | --- | --- | --- |
| [Claude Desktop (beta)](https://code.claude.com/docs/en/desktop-linux) | Anthropic | Ubuntu 22.04+, Debian 12+, amd64/arm64 only | Chat, Cowork and Code tabs, tray, Quick Entry hotkey, signed apt repo |
| [Claude Code CLI](https://code.claude.com/docs/en/install) | Anthropic | Signed apt, dnf and apk repos, so Fedora and RHEL included | Same Claude Code engine, scriptable with `claude -p` |
| [Ubuntu AI roadmap](https://www.phoronix.com/news/Ubuntu-AI-Kill-Switch-Opt-In) | Canonical | Ubuntu 26.10 onward, opt-in | Local inference snaps, Myna speech-to-text, no Claude involved |
| Community repackages (e.g. [claude-desktop-debian](https://github.com/aaddrick/claude-desktop-debian)) | Volunteers | RPM, AppImage, Nix, AUR | The official app repackaged, with small patches |

Claude Desktop on Linux:

- Anthropic says it gives the same Chat, Cowork and Claude Code experience as macOS and Windows, including parallel sessions, diff review, an integrated terminal and editor, and live app preview.
- Cowork runs its tasks in a VM hosted with QEMU and KVM, and needs the user in the `kvm` group.
- Sign-in uses a claude.ai subscription or SSO, and the login is stored in GNOME Keyring or KDE Wallet. API-key auth stays CLI-only.
- Not in the beta yet: Computer Use, dictation, and Fedora/RHEL. The Quick Entry hotkey works on X11, but on native Wayland it needs the desktop's GlobalShortcuts portal.
- Users on GNOME Wayland have [reported](https://claudeissues.com/issue/77810-bug-quick-entry-global-hotkey-cannot-be-configured-on-gnome-wayland-ubuntu-short) that every Quick Entry shortcut is rejected as "already in use".

Claude Code CLI:

- The dnf repo is `https://downloads.claude.ai/claude-code/rpm/stable` (or `/latest`), package `claude-code`, signed with key fingerprint `31DD DE24 DDFA B679 F42D 7BD2 BAA9 29FF 1A7E CACE`.
- Package-manager installs don't self-update. Updates arrive through normal `dnf upgrade`, which suits VIGIL's "RPM and DNF5 own updates" rule.
- It needs a Pro, Max, Team, Enterprise or Console account. The free claude.ai plan doesn't include Claude Code.
- [`claude -p`](https://code.claude.com/docs/en/headless) runs one prompt non-interactively, reads stdin (capped at 10 MB), and can stream JSON events, which is exactly what a launcher needs.
- [`claude-cli://` deep links](https://code.claude.com/docs/en/deep-links) open a terminal with Claude Code in a chosen folder and the prompt typed in but not sent. On Linux it honours `$TERMINAL`.

Canonical's own plans:

- AI features ship as snaps, are opt-in in 26.10, and a setup-wizard choice is planned for 27.04. There's no global kill switch; you remove the snaps.
- Ubuntu 26.10 shipped Myna, a local speech-to-text agent, as the first step, with a fuller desktop assistant aimed at the next LTS.

So the "Claude built into Ubuntu" experience is really Anthropic's Debian package plus its hotkey. Canonical hasn't partnered with Anthropic on any of this as far as I could find.

## What carries over to VIGIL OS

Only the CLI is a clean fit today. Everything else is either unsupported on Fedora or clashes with rules already in AI.md.

| Option | Fit | Why |
| --- | --- | --- |
| Official Claude Desktop | No, not yet | Debian-only. Fedora/RHEL is listed as coming later. Revisit when Anthropic ships an RPM repo. |
| Community RPM of Claude Desktop | No | Repackages and patches Anthropic's proprietary app. Wrong trust model for a signed-repo distro, and a licence question we can't answer for them. |
| Claude Code CLI from Anthropic's dnf repo | Yes | Official, signed, updates through DNF5 like Brave. Works the same on Plasma Wayland and i3 X11. |
| Our own launcher on top of the CLI | Yes | Lets us match VIGIL theming, Rofi/Polybar and KRunner, and the SIERRA safety rules. |
| Canonical's inference snaps | No | Snap-based, Ubuntu-specific. Local models are a SIERRA question, not this one. |

Things the plan has to respect, straight from AI.md:

- A prompt is data, never a shell command.
- Context is explicitly selected. No background screen, clipboard or file collection.
- Say clearly that this is cloud processing, and never silently fall back to something else.
- The desktop stays fully usable without it.
- SELinux stays Enforcing, with no blanket allow rules.
- No proprietary software installed by default. Today that's drivers and RPM Fusion; Claude Code is in the same bucket until we decide otherwise.
- i3 helpers follow `vigilos-i3-session.target`: one instance per session, cleaned up on logout.
- The SIERRA plan already describes a Plasma "Ask" field, a Rofi prompt on i3, a shared task window and Polybar status. VIGIL Ask should use exactly those shapes.

## Design: VIGIL Ask

One small core, two thin front ends, one shared window. The core is the only thing that talks to Claude Code, so swapping in SIERRA later means adding a provider, not rewriting the desktop bits.

Core (`vigil-ask`, Python 3, already in the base image):

- Takes a prompt plus optional context the user picked, runs it through a provider, and streams events to the window.
- Provider 1 is `claude-code`. The provider contract is just ask, stream, cancel and escalate, so SIERRA (or a local model) can slot in as provider 2.
- Writes a non-sensitive status to `$XDG_RUNTIME_DIR/vigil-ask/status` (idle, working, done, failed, needs sign-in, not installed). No prompt text ever goes in there.
- Runs as the user, never root. A user unit tied to the graphical session stops any in-flight run on logout or lock.

How it calls Claude Code for a quick question:

```bash
cd ~/.local/state/vigil-ask/work      # empty dir we own: no .claude/, no .mcp.json
claude -p --output-format stream-json --verbose --include-partial-messages \
  --permission-mode dontAsk \
  --settings /usr/share/vigil-ask/quick-settings.json \
  --append-system-prompt-file /usr/share/vigil-ask/system-prompt.md
```

Why it looks like that:

- **Dedicated empty folder.** Without `--bare`, a `-p` run loads hooks and `.mcp.json` from its working folder with no trust prompt. Running from a folder we control closes that hole.
- **No `--bare`.** Bare mode skips the subscription login and needs an API key, which most users won't have.
- **`dontAsk` plus deny rules.** `quick-settings.json` denies Bash, Edit and Write. Quick Ask answers questions; it doesn't touch the system.
- **Context goes in on stdin.** Selected text or a picked file is piped in with a short header, so Claude never gets path access to the home folder. The 10 MB stdin cap is enforced before sending.
- **Cancel with SIGINT,** which ends the turn cleanly. SIGTERM leaves it half-finished.
- **Follow-ups** reuse the run's `session_id` with `--resume`. A fresh prompt from the launcher always starts a fresh session.

Escalating to real work: an "Open in Claude Code" button asks for a folder, then opens `claude-cli://open?cwd=<folder>&q=<prompt>`. That gives a full interactive session in Konsole or Alacritty with the prompt typed in but not sent, so the user still presses Enter. Claude Code only registers that link handler after the first interactive prompt, so the fallback is launching `$TERMINAL` with `claude` in that folder.

First run and consent:

- Not installed: the window explains what Claude Code is, that it needs a paid Claude plan, and offers a one-click `dnf install claude-code` through pkexec.
- Not signed in: opens a terminal running `claude auth login`.
- First real use shows a one-time notice that prompts and picked context go to Anthropic's servers under the user's account. Turning it off is one setting per user, plus `/etc/vigil-ask/disabled` for the whole machine.

Naming: call it VIGIL Ask, with "Uses Claude Code by Anthropic" in the window. Don't put "Claude" in our own product name or icons without checking Anthropic's brand terms first.

Shared answer window (`vigil-ask-window`, PySide6, used by both editions):

- A prompt field, the streamed answer rendered as Markdown, and chips showing exactly what context is attached.
- Buttons: Stop, Copy, Follow up, Open in Claude Code.
- A small "Cloud: Anthropic" badge so it's always obvious where the text is going.
- Floats by default, small and centred, Escape closes it. It inherits VIGILDark on Plasma and the GTK3 Qt bridge on i3, so no extra theming per edition.

## KDE Plasma edition

Use Plasma's own hooks so it works the same on Wayland without needing the GlobalShortcuts portal that trips up the Electron app.

| Entry point | How | Notes |
| --- | --- | --- |
| KRunner | D-Bus runner (`org.kde.krunner1`) registered in `/usr/share/krunner/dbusplugins/`. Typing `ask <question>` shows an "Ask VIGIL" match that opens the window. | Confirm the Plasma 6 runner metadata format in Phase 4. |
| Global shortcut | `.desktop` file with a default kglobalaccel shortcut, suggested Meta+Shift+A. Opens the window with an empty prompt. | Check it doesn't clash with Plasma defaults; user can rebind in System Settings. |
| Ask about selection | Separate shortcut, suggested Meta+Alt+A, reads the primary selection with `wl-paste --primary` and attaches it as a chip. | Only on that keypress. Nothing reads the selection in the background. Adds `wl-clipboard` as a dependency. |
| Dolphin | Service menu in `/usr/share/kio/servicemenus/`: "Ask about this file" for text-type files under a size limit. | File contents piped on stdin, not a path grant. |
| Escalation | `TERMINAL=konsole` set via `/etc/xdg/plasma-workspace/env/`, so deep links and the fallback open Konsole with the VIGILDark-Konsole profile. |  |
| Done notice | Desktop notification when an answer finishes and the window isn't focused. | Notification says "Answer ready", never the content. |

No Plasma widget in the first cut. KRunner already is the "search field" the SIERRA plan describes, and one fewer thing to maintain. A panel widget can come later if people want a persistent button.

## i3 edition: Rofi and Polybar

Rofi is the prompt, Polybar is the status light, and the shared window shows the answer. Everything goes in the portable defaults in `Skel`, so it stays rebindable and has no fixed monitor assumptions.

Rofi prompt:

- `$mod+Shift+a` runs `vigil-ask prompt`, which opens `rofi -dmenu -l 0 -p "Ask"` with a `vigil-ask.rasi` theme in VIGIL colours (accent `#1763ef`). Enter sends it to the core, which opens the window and streams the answer.
- `$mod+Ctrl+a` does the same but attaches the X11 primary selection from `xclip -o -selection primary`, shown as a chip in the window before anything is sent.
- A second Rofi mode, `vigil-ask history`, lists recent questions so you can reopen one. History is stored locally with mode 0600, kept 30 days by default and configurable.
- Both keybinds are set through variables at the top of the i3 config. They need checking against the current `Skel` i3 config before they're final.

Polybar module:

```ini
[module/vigil-ask]
type = custom/script
exec = vigil-ask status --follow
tail = true
click-left = vigil-ask prompt
click-right = vigil-ask window --last
```

- `status --follow` prints one short glyph plus a word, coloured with the VIGIL palette: idle dimmed, working `#edc652`, done `#1763ef`, failed or sign-in needed `#df3448`.
- When VIGIL Ask is disabled or Claude Code isn't installed, it prints a dimmed glyph that opens the setup screen on click, or nothing if the user turned it off.
- It's tied to the bar's own lifecycle, so there's no extra daemon to manage.

The rest:

- i3 rule: `for_window [class="vigil-ask-window"] floating enable, resize set 900 600, move position center`. Users who want it tiled just delete the line.
- Thunar custom action "Ask about this file" in the `Skel` copy of `uca.xml`, piping the file's contents in the same way as Dolphin.
- `TERMINAL=alacritty` in the i3 session environment, so escalation opens Alacritty.
- The i3lock-color wrapper calls `vigil-ask cancel` before locking. Any helper unit is `PartOf=vigilos-i3-session.target`, so logout cleans up with no masking.
- "Answer ready" notifications through `notify-send`, never including the answer text.

## Packaging and build changes

Three small local RPMs built in the disposable builder like the branding RPM, plus a disabled Anthropic repo definition with a pinned key.

| RPM | Contents | Requires |
| --- | --- | --- |
| `vigil-ask` (noarch) | Core, shared window, quick-settings, system prompt, repo file, pinned key, man page | `python3`, `python3-pyside6` |
| `vigil-ask-plasma` | KRunner runner, shortcut `.desktop`, Dolphin service menu, Plasma env snippet | `vigil-ask`, `wl-clipboard` |
| `vigil-ask-i3` | Rofi theme and scripts, Polybar module, i3 snippet, Thunar action for `Skel` | `vigil-ask`, `rofi`, `xclip`, `polybar` |

None of them `Requires: claude-code`. That keeps installs and updates working when the Anthropic repo is off, and keeps the desktop usable without it.

The Anthropic repo:

- Ship `/etc/yum.repos.d/claude-code.repo` with `enabled=0`, `gpgcheck=1` and `gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-claude-code`.
- The key is fetched at build time and `scripts/lib/build.py` checks its fingerprint against `31DDDE24DDFAB679F42D7BD2BAA929FF1A7ECACE`, the same way the Fedora key is pinned. A mismatch stops the build.
- Disabled by default means nobody's machine contacts Anthropic during routine `dnf` refreshes unless they've opted in.
- The "Install Claude Code" action runs `dnf install --enablerepo=claude-code claude-code` through pkexec, then sets `enabled=1` so future updates arrive with normal system updates and in Discover.
- The baseurl has no `$releasever`, so the identity RPM's libdnf5 override doesn't touch it.

Two ways to handle the binary itself:

- **Option A (recommended): opt-in install.** Integration on by default, binary installed on first use. Same stance as RPM Fusion and proprietary drivers today.
- **Option B: bake it into the ISO** from the verified repo during the build, the way Brave is. Only after confirming Anthropic's terms allow redistribution in a distro image, and with a matching entry in `LICENSES/NOTICE.txt`.

Build and checks:

- `--check` gains source checks for: deny rules present in `quick-settings.json`; repo file has `gpgcheck=1` and the pinned key path; `desktop-file-validate` on every `.desktop`; Rofi theme parses; Polybar module present in the i3 `Skel`; and a unit test that the status file never contains prompt text.
- No SELinux policy changes. Everything runs as the logged-in user, and the install uses the existing polkit path.
- Not a VpM package. VpM only installs under `/opt/vpm`, and this needs to land in system locations owned by RPM.
- No impact on version numbering.

## Rollout and acceptance

Five phases, each gated on the one before. i3 goes first because X11 and Rofi are the simpler target and shake out the core.

1. **Decide.** Option A or B, the product name after a brand-terms check, final keybinds against both `Skel` configs, and who owns the test Claude account. Gate: decisions written into AI.md.
2. **Core and window.** `vigil-ask`, the provider contract, the PySide6 window, the repo file and pinned key. Tested from a terminal in a throwaway Fedora 44 VM. Gate: ask, stream, stop, follow-up and escalate all work, and the deny rules hold.
3. **i3 front end.** Rofi prompt and theme, history mode, Polybar module, Thunar action, lock and logout hooks. Gate: works on an installed i3 VM with SELinux Enforcing.
4. **Plasma front end.** KRunner runner, shortcuts, Dolphin menu, Konsole escalation, on Wayland. Gate: same, on an installed KDE VM.
5. **Build in.** RPMs into the builder, `--check` additions, a full two-edition build, then acceptance on the exact ISO hashes. Gate: the checklist below passes on both editions.

Acceptance checklist (per edition, disposable VMs, 6 GiB max, SELinux Enforcing):

- [ ] Fresh install without Claude Code: desktop fully usable, and `dnf` refreshes make no request to `downloads.claude.ai`
- [ ] KRunner or Polybar shows the setup state, and the setup screen explains the paid-plan requirement
- [ ] Opt-in install through pkexec: pinned key accepted, repo enabled afterwards, `dnf upgrade` and Discover/PackageKit run clean
- [ ] Not signed in: the sign-in terminal opens and the status shows it
- [ ] Signed in: answer streams, Stop cancels cleanly, follow-up resumes the same session
- [ ] Asking it to run a command or edit a file is refused, and nothing in home changes
- [ ] A planted `.claude/settings.json` hook and `.mcp.json` in the user's current folder are not loaded
- [ ] Selection and file context only attach on the explicit action, and the status file never contains prompt text
- [ ] Offline: a clean failed state, no hang
- [ ] Lock and logout cancel an in-flight run, with no leftover processes and one helper per session after re-login
- [ ] Escalation opens Konsole or Alacritty with the prompt typed in but not sent
- [ ] Window and Rofi readable at 1024x768, 1080p and 4K
- [ ] Zero new AVC denials and zero failed units

Record pass, fail and not-run separately with ISO hashes, as with 1.6. The test account's credentials must not end up in evidence archives or screenshots. Physical hardware, Secure Boot and multi-monitor stay "not run" unless actually tested.

## Open decisions and risks

The big call is Option A versus B. Everything else is either a check or something to watch.

- [ ] **Redistribution.** Can Claude Code's binary legally ship inside a VIGIL ISO? Until that's answered in writing, Option A.
- [ ] **Branding.** Is "Ask VIGIL" plus "Uses Claude Code by Anthropic" fine under Anthropic's brand terms, or does it need different wording?
- [ ] **Licence placement.** VIGIL Ask is VIGIL-owned code, so it falls under the Personal Build Licence by default. Decide whether that's what you want for it, given it's meant to be a base feature.
- [ ] **Keybinds.** Confirm Meta+Shift+A, Meta+Alt+A, `$mod+Shift+a` and `$mod+Ctrl+a` are free in both `Skel` configs.
- [ ] **SIERRA overlap.** AI.md says SIERRA isn't authorised yet. Get your sign-off that VIGIL Ask is a separate, smaller feature that SIERRA can later plug into as a provider.

Risks:

- **CLI flags move fast.** Several behaviours this relies on are recent, such as `-p` starting in Manual permission mode from v2.1.302, and `--bare` is due to become the `-p` default. Pin a minimum version in the setup check and cover the call in `--check` with a fake `claude` stub.
- **Paid plans only.** Free claude.ai accounts can't use Claude Code, so a share of users will hit the setup screen and stop. The copy there needs to be honest about it.
- **Cloud dependency.** It's useless offline, and every answer goes to Anthropic. The badge, the first-run notice and the off switch are what keep that honest.
- **Official desktop app arriving on Fedora.** If Anthropic ships an RPM repo later, Quick Entry and Cowork might be worth offering too. VIGIL Ask stays useful either way because it's the Rofi/Polybar/KRunner-native piece the Electron app won't be.

## Sources

Official Anthropic docs (read in full):

- [Claude Desktop on Linux (beta)](https://code.claude.com/docs/en/desktop-linux)
- [Claude Code advanced setup and package repos](https://code.claude.com/docs/en/install)
- [Run Claude Code programmatically (`claude -p`)](https://code.claude.com/docs/en/headless)
- [Launch sessions from links (`claude-cli://`)](https://code.claude.com/docs/en/deep-links)

Coverage and community:

- [OMG! Ubuntu: Claude desktop app for Linux enters beta](https://www.omgubuntu.co.uk/2026/07/claude-desktop-linux-beta)
- [Phoronix: Ubuntu's AI kill switch is removing snaps, initially opt-in](https://www.phoronix.com/news/Ubuntu-AI-Kill-Switch-Opt-In)
- [Let's Data Science: Ubuntu 26.10 ships Myna](https://letsdatascience.com/news/canonical-releases-ubuntu-2610-with-local-speech-to-text-and-12f160a3)
- [heise: Ubuntu 26.10 ships with Linux 7.3 and an AI assistant](https://www.heise.de/en/news/Ubuntu-26-10-ships-with-Linux-7-3-and-an-AI-assistant-11489687.html)
- [Quick Entry hotkey bug on GNOME Wayland](https://claudeissues.com/issue/77810-bug-quick-entry-global-hotkey-cannot-be-configured-on-gnome-wayland-ubuntu-short)
- [aaddrick/claude-desktop-debian (community repackage)](https://github.com/aaddrick/claude-desktop-debian)
