#!/usr/bin/env bash
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO_DIR/scripts/lib/require-builder.sh"
vigilos_require_builder
[[ $# -eq 1 ]] || { echo 'Usage: cleanup-mounts.sh /build/work/vigilos-branding.XXXXXX' >&2; exit 1; }
WORK_ROOT="$(realpath "${VIGIL_WORK_ROOT:-/build/work}")"
WORK_DIR="$(realpath "$1")"
[[ "$WORK_DIR" == "$WORK_ROOT"/vigilos-branding.* && -f "$WORK_DIR/.vigilos-owned" ]] || {
    echo 'ERROR: Only marked work directories owned by this workflow may be unmounted.' >&2; exit 1;
}
for mount_point in run sys proc dev; do
    for root in "$WORK_DIR/squashfs/rootfs" "$WORK_DIR/squashfs"; do
        if mountpoint -q "$root/$mount_point"; then sudo umount "$root/$mount_point"; fi
    done
done
for target in "$WORK_DIR/efi" "$WORK_DIR/squashfs/rootfs" "$WORK_DIR/squashfs" "$WORK_DIR/iso"; do
    if mountpoint -q "$target"; then sudo umount "$target"; fi
done
echo 'Owned mounts released. Working files and logs retained.'
