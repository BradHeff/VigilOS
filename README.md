# VIGIL OS 1.2 “Loopback”

VIGIL OS is a Fedora44-based KDE Plasma Wayland distribution with its own boot, login, desktop and installer identity. This checkout is a development candidate, not a publicly signed production release. Actual build/install evidence and limitations are recorded in [the validation record](docs/VALIDATION-2026-10-21.md); historical progress files do not certify the current candidate.

## Included software

| Purpose | Software |
| --- | --- |
| Desktop | KDE Plasma Wayland, SDDM, Dolphin, Konsole, Kate, Discover |
| Browser | Brave, default for HTTP, HTTPS and HTML |
| Office | LibreOffice Writer, Calc and Impress |
| Development | Node.js24, npm, Python3 |
| Applications | Flatpak available; no automatically installed Flathub apps |
| System packages | RPM/DNF5 with signed Fedora44 repositories and the official signed Brave repository |

Firefox, Fedora bookmarks and the optional Fedora Media Writer application are removed. The live desktop has one **Install VIGIL OS** launcher using Anaconda. Installed systems remove live-only shortcuts, the live account, passwordless live sudo and autologin. Users create their own account in the actual installer; no preconfigured privileged account ships.

SELinux remains Enforcing on live and installed boots. Anaconda temporarily changes enforcement while installing and restores it on normal exit. Guided storage uses Btrfs root/home, ext4 `/boot` and a FAT EFI partition for UEFI. Native hardware, proprietary GPU drivers and Secure Boot acceptance remain outside the completed VM evidence. Four-GiB installation was exercised; this is not a universal hardware minimum guarantee.

## Branding

GRUB, Plymouth, SDDM, Plasma splash, wallpaper, welcome and installer use VIGIL OS. Images preserve their aspect ratios; Plymouth uses the upstream Fedora watermark canvas footprint. The city wallpaper source is **1672×941**; larger exports are accurately described as upscaled derivatives. The product wallpaper lives under `/usr/share/vigilos/wallpapers`; a small product RPM provides the native `F44` wallpaper compatibility directory while preserving Plasma dependencies and original base-art attribution. Public artwork is readable by ordinary desktop users. Existing third-party theme authors, licenses and compatibility IDs are retained. Fedora repository names, signing keys, boot-component provenance, licenses and compatibility metadata intentionally retain their upstream identity.

## Build and test

Read [the isolated test plan](docs/ISOLATED-TEST-PLAN.md) before execution. Use a dedicated, owned disposable Fedora builder. No host package/service/security changes or physical-media writes are part of the validated workflow.

```bash
# Static source checks:
bash scripts/validate.sh
# Inside the prepared disposable builder only:
VIGIL_BUILD_GUEST=1 bash scripts/build-and-brand.sh /path/to/verified-Fedora-KDE.iso
```

The main route remixes a verified official Fedora44 KDE ISO, updates through signed repositories, creates product-owned development RPMs, rebuilds the matching generic live kernel/initramfs and packs an EROFS root into a hybrid BIOS/UEFI ISO. Fedora44 names the payload `LiveOS/squashfs.img`; it is EROFS. Outputs use fresh paths. `pack-prepared-root.sh` and `finish-prepared-image.sh` support reviewed incremental recovery. Legacy composer/kickstart/Alternative routes are not the tested release route.

The private lab is `/home/bheffernan/Documents/Codex/2026-10-21/task-3/vigil-lab`. Its `output/` contains the verified candidate and checksum; `evidence/` contains actual installer, boot, update and visual captures. VM disks, downloads and test outputs are kept outside this source folder. The validation record identifies reused prepared roots and the exact final artifact.

## Package manager roadmap

[VpM](VPM.md) describes the intended native `.vpm` format, signed catalog and transaction architecture. No Rust implementation or native engine is present in this checkout. The initial prototype should inspect/build packages and plan read-only transactions before disposable-root installation. RPM-owned system files remain under rpmdb until an explicit ownership/migration design exists; SQLite commits alone are not OS rollback. AI-generated recipes are untrusted input and must not execute root commands or bypass signatures automatically. The shipping candidate uses supported RPM/DNF5 updates.

## Project map

- `scripts/`: guarded build, branding, package and verification entry points.
- `branding/`, `Skel/`, `PLASMA-CONFIGS/`: product assets and desktop defaults.
- `docs/`: current validation and isolated workflow; `docs/history/` holds superseded handoffs.
- `CLAUDE.md`: current project instructions and evidence locations.
- `blueprints/`, `kickstarts/`: package references and legacy alternatives.

Upstream legal notices and licenses are retained. See `LICENSE` and individual asset/package notices. No public release, push or signing infrastructure was created by this work.

Validated development artifact: candidate033 (actual BIOS/UEFI graphical installs, ISO-free first boots/repeated boots, signed updates, required apps and display matrix). See [the exact validation record](docs/VALIDATION-2026-10-21.md) for checksum, evidence and limits.
