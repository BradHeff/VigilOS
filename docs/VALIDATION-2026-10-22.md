# Fresh KDE and i3 build acceptance — 22 October 2026

These are new images built from the verified official Fedora 44 KDE live ISO and Cloud image through the single `scripts/build-and-brand.sh` entry point. Candidate033 and the 21 October record are historical and do not certify these images. Detailed logs, VM disks and screenshots are retained in `/home/bheffernan/Documents/Codex/2026-10-22/task/work`.

## Artifacts

| Edition | ISO | Bytes | SHA256 |
| --- | --- | ---: | --- |
| KDE | `VIGILOS-1.2-kde-x86_64.iso` | 5,255,397,376 | `50b20901fa43cce7e83460ea09d1cb863f6e457cd804d0ab529fdc0076a7b8bb` |
| i3 | `VIGILOS-1.2-i3-x86_64.iso` | 5,352,718,336 | `dc1d6b2112fbad290d9393bc524f469c93f9b14affabb2a2c410c5521b2e482e` |

Both complete fresh builds passed native ISO media verification, guest-to-host size/SHA256 verification, independent hybrid BIOS/UEFI layout checks and media boot-label consistency checks. Each has a checksum file and a build-evidence archive beside the ISO. KDE build evidence is in `work/build/run-20261022T102410Z/kde`; final i3 evidence is in `work/build/run-20261022T113809Z/i3`.

The final i3 image contains desktop RPM `1.2-2` and branding RPM `1.2-18`; KDE contains branding RPM `1.2-17`. Kernel `7.2.11-200.fc44.x86_64` is present in both. After these image builds, host-only source changes tightened public curl downloads to HTTPS without personal curl configuration and corrected separate Bash syntax checks. They do not change the image payload. This route rebuilds from pinned official inputs but applies current signed repository updates, so future output hashes can differ.

## i3 acceptance

The final image completed a real graphical UEFI Anaconda installation to a blank 48 GiB virtual disk. It then booted without the ISO and authenticated the installer-created account through LightDM into the default **VIGIL OS i3** session. Checks passed for root locking, removal of the live account/sudo/autologin/installer shortcuts, required applications, product and Bash RPM integrity, `dnf check`, Enforcing, no failed units, no coredumps and no kernel OOM/AVC findings in the checked boots.

The city wallpaper appeared on the desktop and greeter. The native greeter file retained its native RPM ownership. Imported GTK/icon/cursor/font defaults, portable Polybar/Rofi/Alacritty settings, private clean Greenclip configuration and the managed i3/locker process tree were checked. Idle activation, wake to a protected lock, password unlock and normal logout passed. The final image's managed session stops its own xss-lock child before X teardown; the preview image's earlier unmanaged xss-lock crash remains recorded in its separate VM.

A signed `dnf upgrade --refresh` followed by native LightDM/i3/i3lock/X-init/Brave reinstallation completed successfully. Brave updated from ISO version `1.97.59` to `1.98.60`. Product integrity, browser defaults, greeter ownership, wallpaper and session defaults survived. A normal graphical Restart, ISO-free boot and password login passed, followed by `FINAL_I3_POST_REBOOT_PASS` with guest UTC evidence at 12:19. An earlier hard reset was recorded separately and is not counted as a normal reboot. The final VM was shut down cleanly.

A separate final-image BIOS live boot reached the actual i3 desktop and showed BIOS firmware, the expected kernel and Enforcing. This was a live boot check, not a fresh BIOS installation. Logs/screenshots are under `work/evidence/final-i3-uefi` and `work/evidence/final-i3-bios`.

The earlier preview UEFI install additionally exercised an actual Brave HTTPS page, LibreOffice conversion and rejection of an incorrect lock password followed by correct authentication. These are identified as preview evidence rather than repeated final-image claims.

## KDE acceptance

The final image reached its branded live Plasma desktop. Required applications, product/Bash RPM integrity, dependencies, shared wallpaper hash, Enforcing and absence of failed units/coredumps passed. Brave was the actual default browser. A first QA-only `xdg-mime` environment warning was corrected by forwarding the real KDE session variables; the clean recheck returned `brave-browser.desktop`.

The earlier KDE live VM ended before installation acceptance was established. It was not counted as a completed installation; the same final ISO was restarted for the real installation described below. This project work did not diagnose or claim to resolve the separately reported host freeze.

The final image completed a fresh graphical UEFI Anaconda installation to its own blank 48 GiB disk. Normal installer exit restored Enforcing, with no failed system units, coredumps or kernel OOM/AVC findings. ISO-free first boot reached the branded SDDM password login and then Plasma. Root locking, removal of the live account/sudo/autologin/installer shortcuts, kernel selection, product/Bash integrity, dependencies and required applications passed. Brave was the actual HTTPS/HTML default and displayed an HTTPS page; LibreOffice produced a PDF; Node/npm/Python/Flatpak version commands succeeded.

Signed upgrades updated Brave to `1.98.60`. Native `sddm`, `sddm-wayland-plasma` and Brave reinstallation completed successfully; product integrity, Enforcing and browser defaults survived. The initial QA command incorrectly requested an uninstalled `sddm-themes` package: the upgrade succeeded but that reinstall request failed. Its log/failed diagnostic unit were retained, and a separate corrected test succeeded. This was not treated as a successful initial test or repaired through a product/security workaround.

A native graphical Restart returned to SDDM. Early QA console switching coincided with one interrupted Wayland session (SDDM recorded signal64), and subsequent automation typed into the returned greeter instead of its intended console. Those incomplete attempts and authentication failures remain recorded. A newly entered ordinary password with no console switching reached Plasma; post-reboot checks passed. A second graceful OS reboot then reached SDDM and the actual Plasma desktop through an uninterrupted password login before diagnostic setup. Final clean-boot package/default/cleanup/security checks passed, with no failed system or user units, no coredumps and no checked kernel OOM/AVC findings. The actual marker `FINAL_KDE_CLEAN_REBOOT_AND_USER_UNITS_PASS` was followed by graceful poweroff. No policy, password, authentication-counter or crash-reporting workaround was applied. Evidence is under `work/evidence/final-kde-uefi`.

The final ISO also reached the actual KDE live desktop under BIOS. The terminal capture at 13:19:52 UTC shows BIOS firmware, kernel `7.2.11-200.fc44.x86_64`, edition `kde`, Enforcing and no failed system units. This is a BIOS live boot check, not a fresh BIOS installation. Evidence is under `work/evidence/final-kde-bios`.

## Scope and limits

Tests use one disposable KVM guest at a time, with 6 GiB RAM, four CPUs, private sockets, user-mode networking and no host devices/shares/credentials. Native Anaconda temporarily relaxes SELinux while installing and restores Enforcing on normal exit. Guest update diagnostics run in detached units with null stdin rather than inheriting the QA serial TTY; no SELinux/PAM exception or crash suppression is installed.

Physical hardware, proprietary GPU drivers, Secure Boot, suspend and every display size are not certified by these fresh-image runs. The previous candidate's broader display/BIOS-install evidence remains historical. These are tested development images with unsigned local product RPMs, not a publicly signed release or a guarantee for every machine.

The only requested host configuration change was the common wallpaper and the backed-up i3 wallpaper startup line. Other host packages, services and security settings were not changed. Source promotion and Git preservation are confirmed only by the generated scoped promotion report; this document alone does not establish that promotion occurred.
