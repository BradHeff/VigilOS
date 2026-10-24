#!/usr/bin/env bash

set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$REPO_DIR/scripts/lib/require-builder.sh"
vigilos_require_builder
source "$REPO_DIR/scripts/lib/product-version.sh"
WORK="$(realpath "$1")"
INPUT="$(readlink -f "$2")"
OUTPUT="$(realpath -m "$3")"
LABEL="${4:-VIGILOS-${VIGIL_VERSION//./-}-${VIGIL_DESKTOP:-kde}-x86_64}"
ROOT="$WORK/squashfs"
STAGE="$WORK/new_iso"
IMAGE="$STAGE/LiveOS/squashfs.img"
[[ -f "$WORK/.vigilos-owned" && -d "$ROOT" && -s "$ROOT/etc/vigilos-release" ]] || { echo 'ERROR: Owned prepared VIGIL root required.' >&2; exit 1; }
[[ -s "$STAGE/boot/x86_64/loader/linux" && -s "$STAGE/boot/x86_64/loader/initrd" ]] || { echo 'ERROR: Prepared kernel/initramfs missing.' >&2; exit 1; }
[[ ! -e "$OUTPUT" && ! -e "$IMAGE" ]] || { echo 'ERROR: Refusing to replace an existing image or output.' >&2; exit 1; }
[[ -f "$INPUT" || -b "$INPUT" ]] || exit 1
bash "$REPO_DIR/scripts/lib/pack-prepared-root.sh" "$WORK" "$IMAGE"
if [[ -f "$STAGE/.discinfo" ]]; then
    printf '%s\n%s\nx86_64\n' "$(date +%s.%N)" "$LABEL" > "$STAGE/.discinfo"
fi
if mountpoint -q "$WORK/iso"; then umount "$WORK/iso"; fi
xorriso -indev "$INPUT" -outdev "$OUTPUT" -map "$STAGE" / -volid "$LABEL" -boot_image any replay -append_partition 1 revoke '' -commit
implantisomd5 --force "$OUTPUT"
checkisomd5 "$OUTPUT"
sha256sum "$OUTPUT" > "$OUTPUT.sha256"
printf 'Verified candidate: %s\n' "$OUTPUT"
