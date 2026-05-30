# CLAUDE.md — ArxisOS

Guidance for Claude Code working in this repository. Read this first.

## What this project is

**ArxisOS** is a **Fedora 43 / KDE Plasma 6 remix** aimed at IT engineers, by Brad Heffernan.
First stable release: **ArxisOS 1.0 "Loopback"** (`VERSION_CODENAME=loopback`).

> Codename note: `Loopback` = `127.0.0.1` / the `lo` interface — networking-themed, nothing
> to do with screen-casting or any remote-access tool. Do **not** rename it without being asked.
> (An earlier "Anycast" suggestion was dropped; "Anycast" is a legit routing method, not a scam
> tool — the scam tool is AnyDesk — but the user chose Loopback regardless.)

## Repository layout

```
blueprints/arxisos-kde.toml      osbuild-composer blueprint (base package set, F43)
kickstarts/arxisos-kde.ks        Alternative build path (livecd-creator / Anaconda)
scripts/
  build-iso.sh                   osbuild-composer: push blueprint, start compose, fetch ISO
  build-and-brand.sh             wrapper → build-iso.sh then apply-composer-branding.sh
  apply-composer-branding.sh     MAIN branding engine (~1700 lines): mount ISO, chroot,
                                 install KDE + branding, repack squashfs + xorrisofs
  cleanup-mounts.sh              emergency unmount/loop-detach (both work dirs)
  validate.sh                    NEW — pre-build sanity checks; run before building
  check-compose.sh               composer status helper
  Alternative/                   apply-branding.sh + build-iso-livecd.sh (older path)
branding/                        plymouth, grub, sddm, plasma-themes, icons, cursors,
                                 wallpapers, logos, aurorae, gtk-themes, fastfetch, skel
Skel/                            /etc/skel seed (bashrc, KDE configs, konsole profile)
PLASMA-CONFIGS/                  reference KDE configs (Archive = not deployed)
REPAIRS.md                       full audit + repair log (read for detail)
```

## Build & test (run on the Fedora 43 host — NOT on Windows)

```bash
# 0. one-time deps
sudo dnf install -y osbuild-composer composer-cli weldr-client \
  squashfs-tools xorriso rsync xz cpio ImageMagick \
  grub2-tools grub2-tools-extra dosfstools pykickstart shellcheck

# 1. sanity-check the tree FIRST (catches CRLF/identity/theme regressions)
./scripts/validate.sh

# 2. build base ISO + apply branding
ISO_DIR="$PWD" ./scripts/build-and-brand.sh

# 3. test in a VM (UEFI; Secure Boot OFF for first run)
qemu-system-x86_64 -m 4096 -enable-kvm -smp 4 \
  -bios /usr/share/edk2/ovmf/OVMF_CODE.fd -cdrom ArxisOS-1.0-x86_64.iso

# 4. in the live VM, confirm identity + theming:
cat /usr/lib/os-release   # PRETTY_NAME="ArxisOS 1.0 (Loopback)"
hostnamectl               # Operating System: ArxisOS 1.0 (Loopback)
ls /usr/share/wallpapers/ArxisOS
kreadconfig6 --file kwinrc --group org.kde.kdecoration2 --key theme
#   → __aurorae__svg__PurPurDayBlur-Aurorae-6
```

> `BUILD_DIR=/home/bheffernan/arxisos-build` is hardcoded in `build-iso.sh` and
> `apply-composer-branding.sh`. Either build from that path, or edit those two lines.

## CRITICAL working rules

1. **LF line endings only.** All `.sh`/`.ks`/dotfiles must stay LF. A CRLF shebang
   (`#!/bin/bash\r`) fails with "exec format error" and the whole build dies. `.gitattributes`
   enforces this; if you edit on a Windows checkout, re-verify (`file x.sh` must say
   "ASCII text executable", not "with CRLF line terminators").
2. **Identity is set in 3 places** — keep them in sync: `apply-composer-branding.sh`,
   `Alternative/apply-branding.sh`, `kickstarts/arxisos-kde.ks`. All write
   **`/usr/lib/os-release`** (canonical) and symlink `/etc/os-release` → it. Never write only
   `/etc/os-release` (Fedora identity leaks via the canonical file otherwise).
3. **Run `./scripts/validate.sh` before every build.**

## Session progress (2026-05-30) — 16-point audit + repair, COMPLETE

Repo was confirmed fully intact (an early tool glitch misreported files as empty — ignore that).
All fixes applied and verified (0 CRLF, all scripts pass `bash -n`):

- **#1 CRLF (build-breaking):** converted 19 files to LF; added `.gitattributes`.
- **#2 os-release leak:** all 3 build paths now write `/usr/lib/os-release` + symlink.
- **#3 Codename:** `Loopback` everywhere (was the placeholder `Plasma`).
- **#4 /etc/issue:** ArxisOS console banners written.
- **#8 Aurorae:** fixed `PurPurDay-Aurorae-6` → `PurPurDayBlur-Aurorae-6` (decorations were
  falling back to Breeze) in `Skel/.config/kwinrc` + `PurPurDay-Global-6/contents/defaults`.
- **#10 Wallpaper:** kickstart now uses the canonical `ArxisOS` KDE package path (+ lowercase
  symlink), not the broken lowercase flat copy.
- **#11 qt5ct:** disabled `QT_QPA_PLATFORMTHEME=qt5ct` in both skels (breaks Qt6); `EDITOR`→`vim`.
- **#12 version regex** in `build-iso.sh` fixed; **#13 cleanup-mounts.sh** now cleans both work dirs.
- **#16 README:** corrected (SELinux is *permissive* not enforcing; ext4 not Btrfs; full prereqs).
- Plymouth (#5), GRUB (#6), SDDM (#7) validated as already-correct.

## Open follow-ups (not blocking a bootable ISO)

- `BUILD_DIR` hardcoded to `/home/bheffernan/arxisos-build` (parameterize if building elsewhere).
- `branding/icons/Vivid-Glassy-Dark-Icons/` referenced but absent (only the unused Night variant
  needs it) — add it or drop the reference.
- `branding/skel/` is not wired into the build (top-level `Skel/` is) — delete one to avoid drift.
- `Screenshots/` missing — add real images or drop the README links.
- Verify on real boot: GRUB theme renders (needs DejaVu `.pf2` fonts generated at build time),
  Plymouth splash shows, SDDM login uses the arxisos theme, desktop wallpaper + decorations apply.

## Next step

User is rebooting into Fedora to run the build. Pick up by running `./scripts/validate.sh`
then `./scripts/build-and-brand.sh`, and triage anything that surfaces in the live VM
(build logs land at `/root/arxisos-*.log`).
