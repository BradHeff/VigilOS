# ArxisOS — Audit & Repair Log

Repairs applied to make ArxisOS produce a correctly-branded, bootable live ISO.
Release set to **ArxisOS 1.0 "Loopback"** (`VERSION_CODENAME=loopback`).

## 16-point audit summary

| # | Area | Finding | Status |
|---|------|---------|--------|
| 1 | Line endings | **All** `.sh`/`.ks`/dotfiles were CRLF → `#!/bin/bash\r` = "exec format error"; nothing would run on Linux | **Fixed** — converted to LF; `.gitattributes` guard added |
| 2 | Distro identity | `/usr/lib/os-release` (canonical, shipped by `fedora-release`) was never overwritten → tools still reported "Fedora" | **Fixed** — both build paths now write `/usr/lib/os-release` and symlink `/etc/os-release` → it |
| 3 | Codename | No release codename; `VERSION_CODENAME=Plasma` (a desktop, not a codename) | **Fixed** — `Loopback` / `loopback` across os-release, lsb-release, system/arxisos-release, kickstart |
| 4 | Console identity | `/etc/issue`, `/etc/issue.net` inherited Fedora text | **Fixed** — branding script writes ArxisOS banners |
| 5 | Plymouth | Custom `arxisos` (two-step) theme installed but composer path intentionally uses `spinner` + ArxisOS watermark for reliability | **Kept** (deliberate, reliable). Theme assets validated present |
| 6 | GRUB | Theme present (`theme.txt`, background, 9-slice assets); `GRUB_DISTRIBUTOR="ArxisOS"`, menu `--class fedora`→`arxisos`, ISO `CDLABEL` patched | OK |
| 7 | SDDM | Complete Qt6 theme; config sets `Current=arxisos` | OK |
| 8 | Plasma theme | Aurorae decoration referenced as `PurPurDay-Aurorae-6` but installed theme is `PurPurDayBlur-Aurorae-6` → decorations fell back to Breeze | **Fixed** in `Skel/.config/kwinrc` and `PurPurDay-Global-6/contents/defaults` |
| 9 | Icons/cursors | `Magna-Glassy-Light-Icons` (default) present; `Vivid-Glassy-Dark-Icons` referenced but absent (guarded no-op, only used by unused Night variant) | Note only |
| 10 | Wallpapers | Kickstart used lowercase `/usr/share/wallpapers/arxisos` flat-copy; canonical is the `ArxisOS` KDE package | **Fixed** — kickstart now installs the `ArxisOS` package + `ArxisOS.png` + lowercase symlink |
| 11 | Skel/Plasma | `QT_QPA_PLATFORMTHEME=qt5ct` forced in `.bashrc` → breaks Qt6 styling (qt5ct not installed) | **Fixed** — commented out in `Skel/.bashrc` and `branding/skel/.bashrc`; `EDITOR/VISUAL`→`vim` |
| 12 | Version strings | `build-iso.sh` version-extraction `sed` was broken (double-escaped) → always fell back | **Fixed** — `sed -E 's/.*"([^"]*)".*/\1/'` |
| 13 | Scripts health | `cleanup-mounts.sh` only cleaned the Alternative work dir, not the composer one | **Fixed** — rewritten to clean both `/var/tmp/arxisos-remaster` and `/var/tmp/arxisos-composer-branding` |
| 14 | Missing refs | `branding/skel/` is unreferenced by any build script (dead weight); `Screenshots/` missing (README) | Note only (not boot/build-critical) |
| 15 | EFI identity | UEFI boot path stays `/boot/efi/EFI/fedora/` | **Intentionally kept** — the signed Secure Boot shim/grub are installed there by `shim-x64`/`grub2-efi-x64`; renaming breaks Secure Boot. Cosmetic only |
| 16 | README vs reality | SELinux claimed "enforcing" (is permissive); claimed Btrfs (uses ext4); incomplete build prereqs | **Fixed** — README corrected; build prereqs + LF note + `validate.sh` added |

## Files changed

- `scripts/apply-composer-branding.sh` — `/usr/lib/os-release`, codename, `/etc/issue`
- `scripts/build-iso.sh` — version regex
- `scripts/cleanup-mounts.sh` — cleans both work dirs
- `scripts/validate.sh` — **new** pre-build checks
- `kickstarts/arxisos-kde.ks` — `/usr/lib/os-release`, codename, wallpaper path
- `Skel/.config/kwinrc`, `branding/plasma-themes/PurPurDay-Global-6/contents/defaults` — Aurorae name
- `Skel/.bashrc`, `branding/skel/.bashrc` — qt5ct/editor
- `.gitattributes` — **new** LF enforcement
- `README.md` — factual corrections + codename

## Build & test (on a Fedora 43 host)

```bash
# 0. one-time deps
sudo dnf install -y osbuild-composer composer-cli weldr-client \
  squashfs-tools xorriso rsync xz cpio ImageMagick \
  grub2-tools grub2-tools-extra dosfstools pykickstart shellcheck

# 1. sanity check the tree
./scripts/validate.sh

# 2. build base ISO + apply branding (wrapper does both)
#    NOTE: scripts hardcode /home/bheffernan/arxisos-build — either run from
#    there or set ISO_DIR and edit BUILD_DIR in build-iso.sh / apply-composer-branding.sh.
ISO_DIR="$PWD" ./scripts/build-and-brand.sh

# 3. test the result in a VM (UEFI; Secure Boot off for first test)
qemu-system-x86_64 -m 4096 -enable-kvm -smp 4 \
  -bios /usr/share/edk2/ovmf/OVMF_CODE.fd \
  -cdrom ArxisOS-1.0-x86_64.iso

# in the live VM, verify identity & theming:
cat /usr/lib/os-release         # PRETTY_NAME="ArxisOS 1.0 (Loopback)"
hostnamectl                     # Operating System: ArxisOS 1.0 (Loopback)
ls /usr/share/wallpapers/ArxisOS
kreadconfig6 --file kwinrc --group org.kde.kdecoration2 --key theme  # __aurorae__svg__PurPurDayBlur-Aurorae-6
```

## Known follow-ups (not blocking a bootable ISO)

- `BUILD_DIR=/home/bheffernan/arxisos-build` is hardcoded in `build-iso.sh` and
  `apply-composer-branding.sh`. Parameterize if building elsewhere.
- `branding/icons/Vivid-Glassy-Dark-Icons/` is referenced but absent — only the
  unused Night variant needs it.
- `branding/skel/` is not wired into the build (the top-level `Skel/` is). Either
  delete it or point the scripts at it to avoid drift.
- Add real `Screenshots/` images or drop those README links.
