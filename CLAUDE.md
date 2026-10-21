# CLAUDE.md — VIGILOS

Guidance for Claude Code working in this repository. Read this first.

## What this project is

**VIGILOS** is a **Fedora 44 / KDE Plasma 6 remix** aimed at IT engineers, by Brad Heffernan.
Current release: **VIGILOS 1.2 "Loopback"** (`VERSION_CODENAME=loopback`). (Was 1.0; the
codename stays `Loopback` across point releases — bump the version number only.)

> Codename note: `Loopback` = `127.0.0.1` / the `lo` interface — networking-themed, nothing
> to do with screen-casting or any remote-access tool. Do **not** rename it without being asked.
> (An earlier "Anycast" suggestion was dropped; "Anycast" is a legit routing method, not a scam
> tool — the scam tool is AnyDesk — but the user chose Loopback regardless.)

## Repository layout

```
blueprints/vigilos-kde.toml      osbuild-composer blueprint (base package set, F44)
kickstarts/vigilos-kde.ks        Alternative build path (livecd-creator / Anaconda)
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

## Build & test (run on the Fedora 44 host — NOT on Windows)

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
  -bios /usr/share/edk2/ovmf/OVMF_CODE.fd -cdrom VIGILOS-1.2-x86_64.iso

# 4. in the live VM, confirm identity + theming:
cat /usr/lib/os-release   # PRETTY_NAME="VIGILOS 1.2 (Loopback)"
hostnamectl               # Operating System: VIGILOS 1.2 (Loopback)
ls /usr/share/wallpapers/VIGILOS
kreadconfig6 --file kwinrc --group org.kde.kdecoration2 --key theme
#   → __aurorae__svg__PurPurDayBlur-Aurorae-6
```

> `BUILD_DIR=/home/bheffernan/vigilos-build` is hardcoded in `build-iso.sh` and
> `apply-composer-branding.sh`. Either build from that path, or edit those two lines.

## CRITICAL working rules

1. **LF line endings only.** All `.sh`/`.ks`/dotfiles must stay LF. A CRLF shebang
   (`#!/bin/bash\r`) fails with "exec format error" and the whole build dies. `.gitattributes`
   enforces this; if you edit on a Windows checkout, re-verify (`file x.sh` must say
   "ASCII text executable", not "with CRLF line terminators").
2. **Identity is set in 3 places** — keep them in sync: `apply-composer-branding.sh`,
   `Alternative/apply-branding.sh`, `kickstarts/vigilos-kde.ks`. All write
   **`/usr/lib/os-release`** (canonical) and symlink `/etc/os-release` → it. Never write only
   `/etc/os-release` (Fedora identity leaks via the canonical file otherwise).
   **Rebranding `ID=vigilos` REQUIRES shipping `/etc/anaconda/profile.d/vigilos.conf`**
   (`base_profile = fedora`, `os_id = vigilos`) in the live env, or Anaconda can't match a
   profile, falls back to `efi_dir="default"`, and the install dies at the bootloader step
   with `gen_grub_cfgstub script failed`. All 3 identity paths now write this file too — keep
   them in sync. `validate.sh` guards it.
3. **Run `./scripts/validate.sh` before every build.**
4. **GPU boot params are load-bearing.** All live + installed kernel cmdlines carry
   `rd.driver.blacklist=nouveau modprobe.blacklist=nouveau nouveau.modeset=0` so the
   image boots on NVIDIA Ada Lovelace / RTX 40xx (nouveau = black-screen-with-cursor).
   Set in 3 places — keep in sync: live `grub.cfg` (EFI+BIOS) and installed
   `GRUB_CMDLINE_LINUX` in `apply-composer-branding.sh`, and `bootloader --append=` in
   the kickstart. The proprietary driver is pulled post-install by
   `vigilos-gpu-setup.service` (NVIDIA-only, network-gated). Don't remove the blacklist;
   it's harmless to AMD/Intel (they use in-kernel KMS).

## Build environment reality (the Fedora host)

- **`sudo` needs a password** here (user is in `wheel`, no `NOPASSWD`; not in `weldr`).
  So `build-iso.sh`, `apply-composer-branding.sh`, and burning a USB **cannot run
  unattended** — they need the password entered interactively. An AFK/auto run can do
  all the *source/doc* edits and `validate.sh`, but not the build or burn.
- **The build dir `/home/bheffernan/vigilos-build` is a *copy*, not the git repo.**
  `build-and-brand.sh` defaults `ISO_DIR=$HOME/vigilos-build` and the scripts hardcode
  `BUILD_DIR=/home/bheffernan/vigilos-build`. Edits made in this git checkout
  (`/media/Windows1/Projects/VIGILOS`) must be **rsynced into that dir before building**
  (it's `bheffernan`-writable, no sudo needed). `scripts/finish-build.sh` does the sync +
  build + brand + burn in one go.

## Session progress (2026-05-30) — 16-point audit + repair, COMPLETE

Repo was confirmed fully intact (an early tool glitch misreported files as empty — ignore that).
All fixes applied and verified (0 CRLF, all scripts pass `bash -n`):

- **#1 CRLF (build-breaking):** converted 19 files to LF; added `.gitattributes`.
- **#2 os-release leak:** all 3 build paths now write `/usr/lib/os-release` + symlink.
- **#3 Codename:** `Loopback` everywhere (was the placeholder `Plasma`).
- **#4 /etc/issue:** VIGILOS console banners written.
- **#8 Aurorae:** fixed `PurPurDay-Aurorae-6` → `PurPurDayBlur-Aurorae-6` (decorations were
  falling back to Breeze) in `Skel/.config/kwinrc` + `PurPurDay-Global-6/contents/defaults`.
- **#10 Wallpaper:** kickstart now uses the canonical `VIGILOS` KDE package path (+ lowercase
  symlink), not the broken lowercase flat copy.
- **#11 qt5ct:** disabled `QT_QPA_PLATFORMTHEME=qt5ct` in both skels (breaks Qt6); `EDITOR`→`vim`.
- **#12 version regex** in `build-iso.sh` fixed; **#13 cleanup-mounts.sh** now cleans both work dirs.
- **#16 README:** corrected (SELinux is *permissive* not enforcing; ext4 not Btrfs; full prereqs).
- Plymouth (#5), GRUB (#6), SDDM (#7) validated as already-correct.

## Open follow-ups (not blocking a bootable ISO)

- `BUILD_DIR` hardcoded to `/home/bheffernan/vigilos-build` (parameterize if building elsewhere).
- `branding/icons/Vivid-Glassy-Dark-Icons/` referenced but absent (only the unused Night variant
  needs it) — add it or drop the reference.
- `branding/skel/` is not wired into the build (top-level `Skel/` is) — delete one to avoid drift.
- `Screenshots/` missing — add real images or drop the README links.
- Verify on real boot: GRUB theme renders (needs DejaVu `.pf2` fonts generated at build time),
  Plymouth splash shows, SDDM login uses the vigilos theme, desktop wallpaper + decorations apply.

## Session progress (2026-05-31) — hardware GPU boot fix + 1.2, BUILT & BURNED

Real-hardware test (i7-13700K + RTX 4080) booted the splash fine but hung at a
**black screen with a top-left cursor** on *Start VIGILOS*. Root cause: `nouveau`
can't drive Ada Lovelace. Fixed + shipped a universal multi-GPU boot path and bumped
to **1.2** (codename unchanged). Details in `REPAIRS.md` (2026-05-31 section).

- **GPU (live + installed):** nouveau blacklist on every kernel cmdline (NVIDIA boots
  via `simpledrm`; AMD/Intel unaffected). `validate.sh` passes; all scripts `bash -n` OK.
- **Installed NVIDIA:** new `vigilos-gpu-setup.service` (first-boot, network-gated)
  installs `akmod-nvidia` + `vigilos-gpu-notify` KDE popup to prompt a reboot.
- **1.2 bump:** all 3 identity paths + blueprint `version="1.2.0"` + ISO name/label.
- **Build + burn DONE:** `scripts/finish-build.sh` ran interactively (one sudo prompt);
  `VIGILOS-1.2-x86_64.iso` built, branded, and written to the USB stick. `sudo` needs a
  password here, so this step is interactive-only (see "Build environment reality").

## Session progress (2026-05-31, later) — installer bootloader-step fix

Live ISO booted fine on the RTX 4080 box (GPU fix from earlier worked) and Anaconda ran;
**install failed at "Installing boot loader"** with
`org.fedoraproject.Anaconda.BootloaderInstallationError: gen_grub_cfgstub script failed`.

- **Root cause:** F44 Anaconda selects its profile (`/etc/anaconda/profile.d/*.conf`) by the
  live env's os-release `ID`/`VARIANT_ID`. Our rebrand to `ID=vigilos` matched no stock
  profile, so Anaconda used built-in defaults where `[Bootloader] efi_dir = "default"`. The
  bootloader step ran `gen_grub_cfgstub /boot/grub2 /boot/efi/EFI/default`, but shim/grub2-efi
  install to `/boot/efi/EFI/fedora`, so `EFI/default` didn't exist → script returns non-zero.
- **Repo fix (all 3 paths + validate.sh):** ship `/etc/anaconda/profile.d/vigilos.conf` with
  `base_profile = fedora` (inherits `efi_dir=fedora` + Fedora storage/bootloader defaults) and
  `[Profile Detection] os_id = vigilos` (auto-selected from our os-release). See rule #2.
- **Current USB (no rebuild needed):** at the GRUB menu press `e` and add **`inst.profile=fedora`**
  to the `linux`/`linuxefi` line, boot, then run the installer — bootloader installs cleanly.
  (Alternatively, before launching the installer, drop the vigilos.conf into the live overlay
  `/etc/anaconda/profile.d/` — the live `/etc` is a writable overlay.)
- **Secondary (cosmetic):** early live boot prints
  `29-parse-livenet.sh: line 6: get_url_handler: command not found` and pauses briefly before
  the splash. The live root is `root=live:CDLABEL=…` (local), so livenet does nothing useful —
  this is dracut's livenet parse hook referencing a `url-lib` function not in the initramfs.
  Non-fatal (boot proceeds). Proper fix is a Fedora-host action: rebuild the live initramfs
  including the `url-lib` dracut module (or drop `livenet`). Not blocking.

## Next step

Re-run the install from the **current USB** using `inst.profile=fedora` (above) to confirm the
bootloader installs and the system boots from disk — no rebuild required. Then rebuild 1.2 with
the repo fix so the profile ships in the image and the boot-option workaround is unnecessary.

After that, boot the installed 1.2 system and confirm it reaches SDDM/desktop. In the live
session you can still verify identity/GPU:

```bash
cat /usr/lib/os-release            # PRETTY_NAME="VIGILOS 1.2 (Loopback)"
cat /proc/cmdline | grep -o 'blacklist=nouveau'   # nouveau blacklisted
lsmod | grep -c nouveau            # expect 0 (nouveau not loaded)
```

If it still hangs: at the GRUB menu press `e`, confirm the `linux` line carries
`rd.driver.blacklist=nouveau modprobe.blacklist=nouveau nouveau.modeset=0`. Logs —
build: `/root/vigilos-*.log`; post-install GPU driver: `/var/log/vigilos-gpu-setup.log`.
