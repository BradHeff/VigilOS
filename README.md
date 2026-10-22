# VIGIL OS 1.2 “Loopback”

VIGIL OS is a Fedora44-based distribution with KDE Plasma Wayland and i3 X11 editions with its own boot, login, desktop and installer identity. This checkout is a development candidate, not a publicly signed production release. Actual build/install evidence and limitations are recorded in [the fresh-build validation record](docs/VALIDATION-2026-10-22.md); historical progress files do not certify the current images.

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

GRUB, Plymouth, SDDM, Plasma splash, wallpaper, welcome and installer use VIGIL OS. Images preserve their aspect ratios; Plymouth uses the upstream Fedora watermark canvas footprint. The city wallpaper source is **1672×941**; larger exports are accurately described as upscaled derivatives. The product wallpaper lives under `/usr/share/vigilos/wallpapers`; a small product RPM provides the native `F44` wallpaper compatibility directory while preserving Plasma dependencies and original base-art attribution. Public artwork is readable by ordinary desktop users. Existing third-party theme authors, licenses and compatibility IDs are retained. Fedora repository names, signing keys, boot-component provenance, licenses and compatibility metadata intentionally retain their upstream identity.

## Build and test

Run one command as your normal host user:

```bash
bash scripts/build-and-brand.sh
```

This builds separate KDE and i3 ISOs using verified official Fedora input and a fresh disposable builder for each. Select one with `--desktop kde` or `--desktop i3`; use `--check` for source/prerequisite checks only. Output ISOs, SHA256 files and build-evidence archives are placed in a fresh timestamped directory under `.build/output/`. No existing output is overwritten. Host dependencies are checked, never installed automatically; all package operations and mounts run inside the builder.

See [the complete build guide](docs/BUILD.md) for requirements, workspace/cache options, i3 shortcuts and script organization. The i3 edition uses your portable dotfile theme with Polybar, Rofi, i3lock-color, Greenclip, Alacritty and LightDM; it omits NVIDIA-specific bar modules and personal machine settings. Both editions use the same VIGIL City wallpaper. Original candidate033 evidence remains historical; new clean-build and live-test evidence is recorded separately.

## Package manager roadmap

[VpM](VPM.md) describes the intended native `.vpm` format, signed catalog and transaction architecture. No Rust implementation or native engine is present in this checkout. The initial prototype should inspect/build packages and plan read-only transactions before disposable-root installation. RPM-owned system files remain under rpmdb until an explicit ownership/migration design exists; SQLite commits alone are not OS rollback. AI-generated recipes are untrusted input and must not execute root commands or bypass signatures automatically. The shipping candidate uses supported RPM/DNF5 updates.

## Project map

- `scripts/`: guarded build, branding, package and verification entry points.
- `branding/`, `Skel/`, `PLASMA-CONFIGS/`: product assets and desktop defaults.
- `docs/`: current validation and isolated workflow; `docs/history/` holds superseded handoffs.
- `CLAUDE.md`: current project instructions and evidence locations.
- `blueprints/`, `kickstarts/`: package references and legacy alternatives.

Upstream legal notices and licenses are retained. See `LICENSE` and individual asset/package notices. No public release, push or signing infrastructure was created by this work.

Current KDE and i3 artifact hashes and actual tests are listed in [the 22 October validation record](docs/VALIDATION-2026-10-22.md). The earlier candidate033 BIOS/UEFI installations and display matrix remain in [the historical record](docs/VALIDATION-2026-10-21.md).
