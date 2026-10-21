# VIGILOS — Audit & Repair Log

Repairs applied to make VIGILOS produce a correctly-branded, bootable live ISO.
Release set to **VIGILOS 1.2 "Loopback"** (`VERSION_CODENAME=loopback`).

## 2026-09-20 — Anaconda GUI would not open in the live session (browser workaround)

**Symptom (real hardware boot test).** The live installer would not start until the
user manually installed a browser in the live session; the browser's WebKit/portal
dependency closure was what actually unblocked Anaconda's web-based UI.

**Root cause.** The live package set included `anaconda` + `anaconda-live` but not the
web UI runtime. Fedora's modern Anaconda GUI is a web UI rendered by WebKitGTK; without
`anaconda-webui` / `webkit2gtk4.1` and a portal backend, the installer window cannot open.

**Fix.** Pinned into BOTH package paths (kept in sync):
- `blueprints/vigilos-kde.toml`: added `anaconda-webui`, `webkit2gtk4.1`,
  `xdg-desktop-portal`, `xdg-desktop-portal-kde` next to the anaconda entries.
- `kickstarts/vigilos-kde.ks` `%packages`: added `xdg-desktop-portal`,
  `anaconda-webui`, `webkit2gtk4.1` (portal-kde was already present).

`validate.sh` passes after the change. Pending: rebuild + hardware retest to confirm
the installer opens standalone.

## 2026-09-20 — repo hygiene follow-ups closed

- Removed dead `Vivid-Glassy-Dark-Icons` references from `apply-composer-branding.sh`
  and `Alternative/apply-branding.sh` (theme was referenced but absent).
- Deleted `branding/skel/` (unwired duplicate); top-level `Skel/` remains canonical.
- README Screenshots section no longer links nonexistent images.

## 2026-05-31 (later) — installer bootloader step: `gen_grub_cfgstub script failed`

**Symptom (real hardware: i7-13700K + RTX 4080).** With the GPU fix in place the live
ISO booted and Anaconda ran. Storage config and software install completed; the install
then died during *System configuration → Installing boot loader* with:

```
org.fedoraproject.Anaconda.BootloaderInstallationError: gen_grub_cfgstub script failed
```

**Root cause.** Fedora 44's Anaconda selects its installer **profile**
(`/etc/anaconda/profile.d/*.conf`) by matching the *live environment's* os-release
`ID`/`VARIANT_ID` (or an `inst.profile=` boot arg). Our branding rewrites the live
os-release to `ID=vigilos`, which matches **no** stock profile, so Anaconda falls back to
built-in defaults — where `[Bootloader] efi_dir = "default"` (the Fedora profile would set
it to `fedora`). At the bootloader step Anaconda runs:

```
gen_grub_cfgstub <config_dir> efi/EFI/<efi_dir>     # i.e. /boot/grub2  /boot/efi/EFI/default
```

but the `shim-x64` / `grub2-efi-x64` packages install the EFI binaries to
`/boot/efi/EFI/**fedora**`. `EFI/default` does not exist, so the stub-generator returns
non-zero and Anaconda raises `BootloaderInstallationError`. (Confirmed against anaconda
`pyanaconda/modules/storage/bootloader/efi.py`: `_efi_config_dir → efi/EFI/{efi_dir}`,
`efi_dir` from `conf.bootloader.efi_dir`, default `"default"`, Fedora profile `"fedora"`.)

**Fix (repo, all 3 identity paths + a validate.sh guard).** Ship an VIGILOS Anaconda
profile in the live env that inherits Fedora:

```ini
# /etc/anaconda/profile.d/vigilos.conf
[Profile]
profile_id = vigilos
base_profile = fedora      # inherits efi_dir=fedora + Fedora storage/bootloader defaults

[Profile Detection]
os_id = vigilos            # matches our rebranded os-release -> auto-selected
```

Written by `apply-composer-branding.sh`, `Alternative/apply-branding.sh`, and
`kickstarts/vigilos-kde.ks` (right after os-release). `validate.sh` now fails the build if
any of the three is missing the profile.

**Current USB — fix without rebuilding.** At the GRUB menu press `e`, append
`inst.profile=fedora` to the `linux`/`linuxefi` line, boot, then run the installer; the
bootloader installs cleanly. (Or, before launching the installer, create the vigilos.conf
above under the live overlay `/etc/anaconda/profile.d/` — the live `/etc` is writable.) The
installed system still gets full VIGILOS identity from the squashfs; the profile only steers
the *installer's* behaviour.

**Secondary (cosmetic, non-blocking).** Early live boot prints
`…/29-parse-livenet.sh: line 6: get_url_handler: command not found` and pauses briefly
before the Plymouth splash. The live root is `root=live:CDLABEL=…` (local media), so the
`livenet` dracut hook has nothing to do — the message is that hook referencing a `url-lib`
helper not present in the initramfs. Boot proceeds. Proper fix (Fedora-host): rebuild the
live initramfs including the `url-lib` dracut module, or drop `livenet`. Left as a follow-up.

## 2026-05-31 — GPU boot fix + 1.2 bump

**Symptom (real hardware: i7-13700K + NVIDIA RTX 4080).** GRUB/Plymouth splash
rendered perfectly, but selecting *Start VIGILOS* dropped to a **black screen with
an X cursor parked top-left** — the desktop never came up.

**Root cause.** The bundled open-source `nouveau` driver cannot mode-set NVIDIA
**Ada Lovelace / RTX 40-series** (4080 = AD103). The splash works because it runs on
the firmware framebuffer (EFI GOP → `efifb`/`simpledrm`); once the kernel loads,
`nouveau` takes the GPU, KMS collapses, and X (`plasmax11`) starts with nothing
drawable — hence the lone cursor.

**Fix — universal multi-GPU boot.** Blacklist `nouveau` on the kernel cmdline so the
generic `simpledrm` framebuffer carries through to the desktop. Targeted (not global
`nomodeset`) so Intel `i915` / AMD `amdgpu` KMS keep full acceleration:
`rd.driver.blacklist=nouveau modprobe.blacklist=nouveau nouveau.modeset=0`.

| Path | Change |
|------|--------|
| `apply-composer-branding.sh` (live ISO) | nouveau blacklist appended to EFI **and** BIOS `grub.cfg` kernel lines (the real build path) |
| `apply-composer-branding.sh` (installed) | nouveau blacklist added to `GRUB_CMDLINE_LINUX` (pre-driver safety net) |
| `apply-composer-branding.sh` (installed) | **new** `vigilos-gpu-setup.service` — first-boot, network-gated, NVIDIA-only: installs `akmod-nvidia` from RPM Fusion + builds the kmod; isolated so failure never blocks the desktop |
| `apply-composer-branding.sh` (installed) | **new** `vigilos-gpu-notify` KDE autostart — one-time popup telling the user to reboot once the NVIDIA driver is built |
| `kickstarts/vigilos-kde.ks` | `bootloader --append=` nouveau blacklist; first-boot installs `akmod-nvidia` when an NVIDIA GPU is present |

Coverage: **NVIDIA** (new + old) boots via `simpledrm` then upgrades to the real
driver post-install; **AMD**/**Intel** boot accelerated out of the box; the existing
*Start VIGILOS (Basic Graphics)* entry (Fedora's `nomodeset`) remains the last resort.

**Version bump → 1.2.** `1.0`→`1.2` across all three identity locations
(`apply-composer-branding.sh`, `kickstarts/vigilos-kde.ks`, `Alternative/apply-branding.sh`),
plus os-release/lsb/issue/system-release, `CPE_NAME` (`:1`→`:1.2`), ISO filename/label
(`VIGILOS-1.2-x86_64.iso` / `VIGILOS-1-2-x86_64`), and blueprint `version = "1.2.0"`.
Codename **Loopback** unchanged. Also re-stripped CRLF from `blueprints/vigilos-kde.toml`
(Windows-mount regression). `validate.sh` passes.

**Build + burn.** `scripts/finish-build.sh` (new) runs the root-only steps
interactively (one sudo prompt — required, as this host has no passwordless sudo and
the user isn't in `weldr`): syncs the repo into `/home/bheffernan/vigilos-build`,
validates, builds via composer, applies branding, then writes the ISO to USB with
safety guards (USB-bus only; refuses any disk with system mountpoints — an internal
SSD sits on the USB bus here; re-type-to-confirm). **`VIGILOS-1.2-x86_64.iso` was built,
branded, and burned to USB this session.** Pending: real-hardware boot confirmation on
the i7-13700K / RTX 4080.

## 16-point audit summary

| # | Area | Finding | Status |
|---|------|---------|--------|
| 1 | Line endings | **All** `.sh`/`.ks`/dotfiles were CRLF → `#!/bin/bash\r` = "exec format error"; nothing would run on Linux | **Fixed** — converted to LF; `.gitattributes` guard added |
| 2 | Distro identity | `/usr/lib/os-release` (canonical, shipped by `fedora-release`) was never overwritten → tools still reported "Fedora" | **Fixed** — both build paths now write `/usr/lib/os-release` and symlink `/etc/os-release` → it |
| 3 | Codename | No release codename; `VERSION_CODENAME=Plasma` (a desktop, not a codename) | **Fixed** — `Loopback` / `loopback` across os-release, lsb-release, system/vigilos-release, kickstart |
| 4 | Console identity | `/etc/issue`, `/etc/issue.net` inherited Fedora text | **Fixed** — branding script writes VIGILOS banners |
| 5 | Plymouth | Custom `vigilos` (two-step) theme installed but composer path intentionally uses `spinner` + VIGILOS watermark for reliability | **Kept** (deliberate, reliable). Theme assets validated present |
| 6 | GRUB | Theme present (`theme.txt`, background, 9-slice assets); `GRUB_DISTRIBUTOR="VIGILOS"`, menu `--class fedora`→`vigilos`, ISO `CDLABEL` patched | OK |
| 7 | SDDM | Complete Qt6 theme; config sets `Current=vigilos` | OK |
| 8 | Plasma theme | Aurorae decoration referenced as `PurPurDay-Aurorae-6` but installed theme is `PurPurDayBlur-Aurorae-6` → decorations fell back to Breeze | **Fixed** in `Skel/.config/kwinrc` and `PurPurDay-Global-6/contents/defaults` |
| 9 | Icons/cursors | `Magna-Glassy-Light-Icons` (default) present; `Vivid-Glassy-Dark-Icons` referenced but absent (guarded no-op, only used by unused Night variant) | Note only |
| 10 | Wallpapers | Kickstart used lowercase `/usr/share/wallpapers/vigilos` flat-copy; canonical is the `VIGILOS` KDE package | **Fixed** — kickstart now installs the `VIGILOS` package + `VIGILOS.png` + lowercase symlink |
| 11 | Skel/Plasma | `QT_QPA_PLATFORMTHEME=qt5ct` forced in `.bashrc` → breaks Qt6 styling (qt5ct not installed) | **Fixed** — commented out in `Skel/.bashrc` and `branding/skel/.bashrc`; `EDITOR/VISUAL`→`vim` |
| 12 | Version strings | `build-iso.sh` version-extraction `sed` was broken (double-escaped) → always fell back | **Fixed** — `sed -E 's/.*"([^"]*)".*/\1/'` |
| 13 | Scripts health | `cleanup-mounts.sh` only cleaned the Alternative work dir, not the composer one | **Fixed** — rewritten to clean both `/var/tmp/vigilos-remaster` and `/var/tmp/vigilos-composer-branding` |
| 14 | Missing refs | `branding/skel/` is unreferenced by any build script (dead weight); `Screenshots/` missing (README) | Note only (not boot/build-critical) |
| 15 | EFI identity | UEFI boot path stays `/boot/efi/EFI/fedora/` | **Intentionally kept** — the signed Secure Boot shim/grub are installed there by `shim-x64`/`grub2-efi-x64`; renaming breaks Secure Boot. Cosmetic only |
| 16 | README vs reality | SELinux claimed "enforcing" (is permissive); claimed Btrfs (uses ext4); incomplete build prereqs | **Fixed** — README corrected; build prereqs + LF note + `validate.sh` added |

## Files changed

- `scripts/apply-composer-branding.sh` — `/usr/lib/os-release`, codename, `/etc/issue`
- `scripts/build-iso.sh` — version regex
- `scripts/cleanup-mounts.sh` — cleans both work dirs
- `scripts/validate.sh` — **new** pre-build checks
- `kickstarts/vigilos-kde.ks` — `/usr/lib/os-release`, codename, wallpaper path
- `Skel/.config/kwinrc`, `branding/plasma-themes/PurPurDay-Global-6/contents/defaults` — Aurorae name
- `Skel/.bashrc`, `branding/skel/.bashrc` — qt5ct/editor
- `.gitattributes` — **new** LF enforcement
- `README.md` — factual corrections + codename

## Build & test (on a Fedora 44 host)

```bash
# 0. one-time deps
sudo dnf install -y osbuild-composer composer-cli weldr-client \
  squashfs-tools xorriso rsync xz cpio ImageMagick \
  grub2-tools grub2-tools-extra dosfstools pykickstart shellcheck

# 1. sanity check the tree
./scripts/validate.sh

# 2. build base ISO + apply branding (wrapper does both)
#    NOTE: scripts hardcode /home/bheffernan/vigilos-build — either run from
#    there or set ISO_DIR and edit BUILD_DIR in build-iso.sh / apply-composer-branding.sh.
ISO_DIR="$PWD" ./scripts/build-and-brand.sh

# 3. test the result in a VM (UEFI; Secure Boot off for first test)
qemu-system-x86_64 -m 4096 -enable-kvm -smp 4 \
  -bios /usr/share/edk2/ovmf/OVMF_CODE.fd \
  -cdrom VIGILOS-1.2-x86_64.iso

# in the live VM, verify identity & theming:
cat /usr/lib/os-release         # PRETTY_NAME="VIGILOS 1.2 (Loopback)"
hostnamectl                     # Operating System: VIGILOS 1.2 (Loopback)
ls /usr/share/wallpapers/VIGILOS
kreadconfig6 --file kwinrc --group org.kde.kdecoration2 --key theme  # __aurorae__svg__PurPurDayBlur-Aurorae-6
```

## Known follow-ups (not blocking a bootable ISO)

- `BUILD_DIR=/home/bheffernan/vigilos-build` is hardcoded in `build-iso.sh` and
  `apply-composer-branding.sh`. Parameterize if building elsewhere.
- `branding/icons/Vivid-Glassy-Dark-Icons/` is referenced but absent — only the
  unused Night variant needs it.
- `branding/skel/` is not wired into the build (the top-level `Skel/` is). Either
  delete it or point the scripts at it to avoid drift.
- Add real `Screenshots/` images or drop those README links.
