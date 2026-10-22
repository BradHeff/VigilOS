# VIGIL OS project handoff

VIGIL OS 1.2 “Loopback” is a Fedora44-based KDE Plasma Wayland development distribution. Keep the Loopback codename. The current user goal is a coherent independent product identity while retaining upstream compatibility, provenance and licenses. VpM is a separate native-package-manager design, not implemented production software.

## Authoritative build route

Read `README.md`, `docs/ISOLATED-TEST-PLAN.md` and `docs/VALIDATION-2026-10-21.md`. The tested route starts with a checksum/signature-verified official Fedora44 KDE live ISO inside an owned disposable Fedora builder. `scripts/build-and-brand.sh` calls `apply-composer-branding.sh`; it does not start osbuild-composer. Product assets and identity are packaged by `package-branding.sh` and `package-release-common.sh`. `pack-prepared-root.sh` supports reviewed incremental candidate recovery and encodes target SELinux contexts directly into EROFS. The live payload retains Fedora's filename `LiveOS/squashfs.img`, despite being EROFS.

All custom installation, package operations, mounts, chroots and initramfs generation belong inside the disposable builder. The marker and `VIGIL_BUILD_GUEST=1` guard prevent accidental host execution; they are not a security sandbox. Do not install host dependencies, start host daemons, weaken host SELinux/firewalls/KVM permissions, attach physical disks or write USB. The current lab serializes VMs with a lock and uses only owned QCOW2 disks, read-only media and private Unix control sockets. No host shares or credentials. Preserve old outputs.

## Current product behavior

- Plasma Wayland with SDDM, VIGIL GRUB/Plymouth/splash/login/wallpaper/installer identity. Preserve aspect ratios and the Fedora-sized Plymouth footprint. The city artwork is native1672×941; larger derivatives are upscaled. Theme previews must show real VIGIL captures and retain upstream authors/licenses.
- Exactly one live desktop launcher, `Install VIGIL OS`; Fedora's duplicate is hidden without removing Anaconda. Installer-only Brave profile uses basic credential storage for the empty-password live account and is removed on normal exit. Normal installed Brave keeps normal credential-store behavior and Chromium sandboxing.
- Brave is default HTTP/HTTPS/HTML handler, obtained from its official signed repository. Firefox, Fedora bookmarks and the optional Fedora Media Writer application are absent. LibreOffice Writer/Calc/Impress, Node24/npm, Python3 and Flatpak are included. No automatic Flathub applications, RPMFusion or proprietary drivers in this pass.
- RPM/DNF5 and rpmdb remain authoritative for system updates. Keep upstream GPG verification, Fedora repository releasever44, signed shim/GRUB provenance and compatibility metadata. Custom product RPMs are unsigned local development artifacts; no public signed release repository exists.
- Enforcing live/installed boots. Upstream Anaconda temporarily relaxes enforcement while installing and restores it on normal exit. No blanket allow rules. Run diagnostic DNF mutations in detached guest units with null stdin/journal output to avoid inheriting the private serial TTY: an actual `load_policy_t` denial was traced to that test harness, not Brave.
- Normal account creation, root locked, correct newest kernel initially, no redundant Plasma Setup, and installed removal of live user/autologin/sudo/installer shortcuts. Optional Git prompt support must not break shell startup.

## Evidence and historical notes

The lab at `/home/bheffernan/Documents/Codex/2026-10-21/task-3/vigil-lab` contains candidate ISOs, exact logs/screenshots, `evidence/ACCEPTANCE.json` and the source change manifest. Do not infer successful tests from historical prose. `docs/VALIDATION-2026-10-21.md` summarizes only actual runs and clearly labels remaining limits. Synchronize final source to `/home/bheffernan/Project/VigilOS` only under a verified scoped backup, preserving original `.git` and the two protected unreadable legacy ISO files; the latest lab promotion record, not this prose, confirms completion.

The previous handoff is preserved at `docs/history/CLAUDE-before-isolated-validation.md` for context. Its old composer/host setup, privileged repair and USB instructions are not the current workflow. Other history and progress files remain historical records. No commits, pushes, publication or release-signing credentials were created by this work.
