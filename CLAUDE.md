# VIGIL OS project handoff

VIGIL OS 1.2 “Loopback” is a Fedora44-based development distribution with KDE Plasma Wayland and i3 X11 editions. Keep the Loopback codename. The current user goal is a coherent independent product identity while retaining upstream compatibility, provenance and licenses. VpM is a separate native-package-manager design, not implemented production software.

## Authoritative build route

Read `README.md` and `docs/BUILD.md`. The only user build entry point is `bash scripts/build-and-brand.sh`, run as the normal host user. It verifies pinned signed Fedora inputs, boots fresh disposable cloud overlays sequentially, installs builder dependencies in each VM and invokes the complete fresh root preparation/branding/pack/ISO route. `--desktop kde|i3|both` selects editions. Active implementation lives in `scripts/lib`; installed product helpers live in `scripts/runtime`. Superseded composer/livecd scripts and old host cleanup/setup wrappers were removed. Never restore them as alternative user routes.

All package operations, mounts, chroots and initramfs generation belong inside the disposable builder. The marker and `VIGIL_BUILD_GUEST=1` guard prevent accidental host execution; they are not a security sandbox. No host dependency installation, daemons, security changes, physical media or host shares. Builder SSH uses task-generated ephemeral keys and loopback forwarding only; never use personal SSH keys or inspect credentials. Preserve existing outputs and earlier candidate033 evidence. `.build` is private disposable state and excluded from Git.

The user explicitly authorized changing the current host wallpaper to the shared ISO wallpaper. This was applied with a separate backed-up i3 wallpaper-line change, not as part of ISO build execution. Do not broaden that authorization into host package or security changes.

The i3 edition imports sanitized user configs, fonts/licenses, the exact Git prompt helper and relevant local controls. Keep personal exports, fixed monitor assignments, clipboard history and NVIDIA-only bar modules out of shipped defaults. Preserve upstream PAM authentication for the color lock and use the shared wallpaper for desktop/greeter/lock.

## Current product behavior

- Plasma Wayland with SDDM, VIGIL GRUB/Plymouth/splash/login/wallpaper/installer identity. Preserve aspect ratios and the Fedora-sized Plymouth footprint. The city artwork is native1672×941; larger derivatives are upscaled. Theme previews must show real VIGIL captures and retain upstream authors/licenses.
- Exactly one live desktop launcher, `Install VIGIL OS`; Fedora's duplicate is hidden without removing Anaconda. Installer-only Brave profile uses basic credential storage for the empty-password live account and is removed on normal exit. Normal installed Brave keeps normal credential-store behavior and Chromium sandboxing.
- Brave is default HTTP/HTTPS/HTML handler, obtained from its official signed repository. Firefox, Fedora bookmarks and the optional Fedora Media Writer application are absent. LibreOffice Writer/Calc/Impress, Node24/npm, Python3 and Flatpak are included. No automatic Flathub applications, RPMFusion or proprietary drivers in this pass.
- RPM/DNF5 and rpmdb remain authoritative for system updates. Keep upstream GPG verification, Fedora repository releasever44, signed shim/GRUB provenance and compatibility metadata. Custom product RPMs are unsigned local development artifacts; no public signed release repository exists.
- Enforcing live/installed boots. Upstream Anaconda temporarily relaxes enforcement while installing and restores it on normal exit. No blanket allow rules. Run diagnostic DNF mutations in detached guest units with null stdin/journal output to avoid inheriting the private serial TTY: an actual `load_policy_t` denial was traced to that test harness, not Brave.
- Normal account creation, root locked, correct newest kernel initially, no redundant Plasma Setup, and installed removal of live user/autologin/sudo/installer shortcuts. Optional Git prompt support must not break shell startup.

## Evidence and historical notes

Fresh KDE/i3 builds and acceptance for this script cleanup live in `/home/bheffernan/Documents/Codex/2026-10-22/task/work`. Read `docs/VALIDATION-2026-10-22.md` and the actual evidence before making acceptance claims. The source recovery/promotion record is `work/evidence/LATEST-PROMOTION.json`; source parity and original Git preservation must pass before treating the Project checkout as updated. Build logs, private ephemeral keys and VM disks stay outside public source.

The lab at `/home/bheffernan/Documents/Codex/2026-10-21/task-3/vigil-lab` contains candidate ISOs, exact logs/screenshots, `evidence/ACCEPTANCE.json` and the source change manifest. Do not infer successful tests from historical prose. `docs/VALIDATION-2026-10-21.md` summarizes only actual runs and clearly labels remaining limits. Synchronize final source to `/home/bheffernan/Project/VigilOS` only under a verified scoped backup, preserving original `.git` and the two protected unreadable legacy ISO files; the latest lab promotion record, not this prose, confirms completion.

The previous handoff is preserved at `docs/history/CLAUDE-before-isolated-validation.md` for context. Its old composer/host setup, privileged repair and USB instructions are not the current workflow. Other history and progress files remain historical records. No commits, pushes, publication or release-signing credentials were created by this work.
