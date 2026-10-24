# VIGIL OS

VIGIL OS is a Fedora44-based distribution with KDE Plasma Wayland and i3 X11 editions with its own boot, login, desktop and installer identity. This checkout is a development candidate, not a publicly signed production release. The build script now allocates a persistent product version for each real build; see [version numbering](docs/BUILD.md#version-numbering). The three manual-build update/theme defects are repaired in the maintained source. The earlier version 1.2 KDE and i3 rebuilds passed the VM checks in [the repaired-build report](docs/REPAIRED-BUILD-VALIDATION-2026-10-24.md), including fresh UEFI installation, updates, authentication and display checks. The original manual images and their failure record are preserved. Hardware and Secure Boot remain untested.

## Included software

| Purpose | Software |
| --- | --- |
| KDE desktop | Plasma Wayland, SDDM, Dolphin, Konsole, Kate, Discover |
| i3 desktop | i3 X11, LightDM, Polybar, Rofi, i3lock-color, Greenclip, Alacritty, Thunar |
| Browser | Brave, default for HTTP, HTTPS and HTML |
| Office | LibreOffice Writer, Calc and Impress |
| Development | Node.js24, npm, Python3 |
| Applications | Flatpak available; no automatically installed Flathub apps |
| System packages | RPM/DNF5 with signed Fedora44 repositories and the official signed Brave repository |

Firefox, Fedora bookmarks and the optional Fedora Media Writer application are removed. The live desktop has one **Install VIGIL OS** launcher using Anaconda. Installed systems remove live-only shortcuts, the live account, passwordless live sudo and autologin. Users create their own account in the actual installer; no preconfigured privileged account ships.

SELinux remains Enforcing on live and installed boots. Anaconda temporarily changes enforcement while installing and restores it on normal exit. Guided storage uses Btrfs root/home, ext4 `/boot` and a FAT EFI partition for UEFI. Native hardware, proprietary GPU drivers and Secure Boot acceptance remain outside the completed VM evidence. Fresh acceptance uses six-GiB guests; the older candidate033 also exercised four-GiB installation. Neither establishes a universal hardware minimum.

## Branding

GRUB, Plymouth, SDDM, Plasma splash, wallpaper, welcome and installer use VIGIL OS. Images preserve their aspect ratios; Plymouth uses the upstream Fedora watermark canvas footprint. The active dark wallpaper variants are user-supplied at 1920×1080, 2560×1600, 3440×1440 and 3840×2160. Their creation/upscale history is unknown; the previous city source remains historical. The product wallpaper lives under `/usr/share/vigilos/wallpapers`; a small product RPM provides the native `F44` wallpaper compatibility directory while preserving Plasma dependencies and original base-art attribution. Public artwork is readable by ordinary desktop users. Existing third-party theme authors, licenses and compatibility IDs are retained. Fedora repository names, signing keys, boot-component provenance, licenses and compatibility metadata intentionally retain their upstream identity.

## Build and test

Run one command as your normal host user:

```bash
bash scripts/build-and-brand.sh
```

This builds separate KDE and i3 ISOs using verified official Fedora input and a fresh disposable builder for each. Select one with `--desktop kde` or `--desktop i3`; use `--check` for source/prerequisite checks only. Output ISOs, SHA256 files and build-evidence archives are placed in a fresh timestamped directory under `.build/output/`. No existing output is overwritten. Host dependencies are checked, never installed automatically; all package operations and mounts run inside the builder.

Automatic numbering was initialized for **1.3 (Loopback)**; read `version.json` for the current next version. `version.json` keeps the manually controlled first number/codename and the next automatic second number. Both editions in one run share a version, and deleting `.build` does not reset the counter. The versioning change passed source and regression checks; no new ISO has been rebuilt for this change. See [the versioning record](docs/VERSIONING-2026-10-25.md).

See [the complete build guide](docs/BUILD.md) for requirements, workspace/cache options, i3 shortcuts and script organization. The i3 edition uses your portable dotfile theme with Polybar, Rofi, i3lock-color, Greenclip, Alacritty and LightDM; it omits NVIDIA-specific bar modules and personal machine settings. Both editions use the supplied dark faded-mark wallpaper, with resolution variants; KDE defaults to the PurPurNight Plasma style and VIGIL Dark palette. Original candidate033 evidence remains historical; new clean-build and live-test evidence is recorded separately.

## SIERRA roadmap

[SIERRA desktop integration](docs/SIERRA-INTEGRATION-PLAN.md) is a future development proposal. No SIERRA services, launchers or automation are implemented by this theme change.

## Package manager roadmap

[VpM](VPM.md) describes the intended native `.vpm` format, signed catalog and transaction architecture. No Rust implementation or native engine is present in this checkout. The initial prototype should inspect/build packages and plan read-only transactions before disposable-root installation. RPM-owned system files remain under rpmdb until an explicit ownership/migration design exists; SQLite commits alone are not OS rollback. AI-generated recipes are untrusted input and must not execute root commands or bypass signatures automatically. The shipping candidate uses supported RPM/DNF5 updates.

## Project map

- `scripts/`: guarded build, branding, package and verification entry points.
- `branding/`, `Skel/`, `PLASMA-CONFIGS/`: product assets and desktop defaults.
- `docs/`: current validation and isolated workflow; `docs/history/` holds superseded handoffs.
- `CLAUDE.md`: current project instructions and evidence locations.
- `blueprints/`, `kickstarts/`: package references and legacy alternatives.

Upstream legal notices and licenses are retained. See `LICENSE` and individual asset/package notices. No public release, push or signing infrastructure was created by this work.

Current repaired ISO paths, checksums, actual tests and limitations are listed in [the repaired-build report](docs/REPAIRED-BUILD-VALIDATION-2026-10-24.md). The [original manual-build report](docs/MANUAL-BUILD-VALIDATION-2026-10-24.md) retains the original artifact hashes and three failures. The previous [dark-theme validation record](docs/DARK-THEME-VALIDATION.md) describes earlier artifacts. The [22 October script-cleanup record](docs/VALIDATION-2026-10-22.md) remains historical. The earlier candidate033 BIOS/UEFI installations and display matrix remain in [the historical record](docs/VALIDATION-2026-10-21.md).
