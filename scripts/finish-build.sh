#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------
# ArxisOS — one-shot finisher: sync → validate → build → brand → burn
#
# Runs the steps that need root (composer build, branding loop-mounts,
# USB write) which CANNOT run unattended on this host because sudo
# requires a password. Run this yourself; it asks for the password once.
#
#   ./scripts/finish-build.sh                 # build, then offer to burn
#   ./scripts/finish-build.sh /dev/sdX        # build, then burn to /dev/sdX
#   SKIP_BUILD=1 ./scripts/finish-build.sh    # just burn the existing ISO
# ------------------------------------------------------------

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${BUILD_DIR:-/home/bheffernan/arxisos-build}"
ISO_NAME="${ISO_NAME:-ArxisOS-1.2-x86_64.iso}"
TARGET_DEV="${1:-}"

say()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m[!] %s\033[0m\n' "$*" >&2; }
die()  { printf '\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

[[ -d "$REPO_DIR" ]] || die "repo dir not found: $REPO_DIR"

# Warm the sudo timestamp up-front so the long build doesn't stall waiting
# for a password halfway through.
say "Authenticating (sudo) — enter your password once"
sudo -v || die "sudo authentication failed"
# Keep the timestamp alive for the duration of the build.
( while true; do sudo -n true 2>/dev/null || exit; sleep 50; done ) &
SUDO_KEEPALIVE=$!
trap 'kill "$SUDO_KEEPALIVE" 2>/dev/null || true' EXIT

if [[ "${SKIP_BUILD:-0}" != "1" ]]; then
    say "Syncing repo → build dir: $BUILD_DIR"
    mkdir -p "$BUILD_DIR"
    rsync -a --delete \
        --exclude '.git' \
        --exclude '*.iso' \
        --exclude '*.jpg' \
        --exclude '*.png.bak' \
        "$REPO_DIR"/ "$BUILD_DIR"/

    say "Running validate.sh"
    ( cd "$BUILD_DIR" && ./scripts/validate.sh ) || die "validate.sh failed — fix before building"

    say "Building ISO + applying branding (this takes a while)"
    ( cd "$BUILD_DIR" && ISO_DIR="$BUILD_DIR" ./scripts/build-and-brand.sh ) || die "build/branding failed"
fi

ISO_PATH="$BUILD_DIR/$ISO_NAME"
if [[ ! -f "$ISO_PATH" ]]; then
    # Fall back to newest ArxisOS-*.iso if the exact name moved.
    ISO_PATH="$(ls -1t "$BUILD_DIR"/ArxisOS-*.iso 2>/dev/null | head -1 || true)"
fi
[[ -f "$ISO_PATH" ]] || die "no finished ISO found in $BUILD_DIR"
say "Finished ISO: $ISO_PATH ($(du -h "$ISO_PATH" | cut -f1))"

# ---------------- USB burn (destructive — be careful) ----------------
say "USB burn"
echo "Removable USB disks detected:"
mapfile -t USB_DEVS < <(lsblk -dno NAME,TRAN,TYPE | awk '$2=="usb" && $3=="disk"{print $1}')
if (( ${#USB_DEVS[@]} == 0 )); then
    warn "No USB disk detected. Plug it in and re-run:  SKIP_BUILD=1 ./scripts/finish-build.sh /dev/sdX"
    exit 0
fi
lsblk -o NAME,SIZE,TRAN,MODEL,MOUNTPOINT $(printf '/dev/%s ' "${USB_DEVS[@]}")

if [[ -z "$TARGET_DEV" ]]; then
    if (( ${#USB_DEVS[@]} == 1 )); then
        TARGET_DEV="/dev/${USB_DEVS[0]}"
    else
        read -rp "Enter target device (e.g. /dev/sdb), or blank to skip: " TARGET_DEV
        [[ -z "$TARGET_DEV" ]] && { warn "Skipped USB burn."; exit 0; }
    fi
fi

# Safety checks before writing.
[[ -b "$TARGET_DEV" ]] || die "$TARGET_DEV is not a block device"
DEV_BASE="$(basename "$TARGET_DEV")"
TRAN="$(lsblk -dno TRAN "$TARGET_DEV" 2>/dev/null || true)"
[[ "$TRAN" == "usb" ]] || die "$TARGET_DEV is not on the USB bus (tran=$TRAN) — refusing to write"

# Refuse if ANY partition of the target is mounted at a critical/system path.
# (On this host an internal SSD — /boot, /home — is on the USB bus too; never write it.)
while read -r mp; do
    [[ -z "$mp" ]] && continue
    case "$mp" in
        /|/boot|/boot/efi|/home|/usr|/var|/etc|/media/*|/run/media/*|/mnt/*)
            die "$TARGET_DEV has a partition mounted at '$mp' — this looks like a system/data disk, refusing" ;;
    esac
done < <(lsblk -lno MOUNTPOINT "$TARGET_DEV")

# Belt-and-braces: refuse if the device hosts the running root filesystem.
ROOT_SRC="$(findmnt -no SOURCE / 2>/dev/null || true)"
if [[ "$ROOT_SRC" == *"$DEV_BASE"* ]]; then
    die "$TARGET_DEV appears to host the running system — refusing"
fi

echo
warn "About to ERASE $TARGET_DEV and write $ISO_NAME. ALL DATA ON IT WILL BE LOST."
lsblk -o NAME,SIZE,MODEL,MOUNTPOINT "$TARGET_DEV"
read -rp "Type the device name again to confirm ($TARGET_DEV): " CONFIRM
[[ "$CONFIRM" == "$TARGET_DEV" ]] || die "confirmation mismatch — aborted"

# Unmount any mounted partitions of the target first.
for part in $(lsblk -lno NAME "$TARGET_DEV" | tail -n +2); do
    sudo umount "/dev/$part" 2>/dev/null || true
done

say "Writing ISO → $TARGET_DEV (dd)"
sudo dd if="$ISO_PATH" of="$TARGET_DEV" bs=4M status=progress oflag=direct conv=fsync
sync
say "Done ✅  You can now boot $TARGET_DEV on the target hardware."
