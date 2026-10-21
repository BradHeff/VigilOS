#!/usr/bin/env bash
# Pack only an owned prepared root; assembly can use bounded artifact transfer.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO_DIR/scripts/lib/require-builder.sh"
vigilos_require_builder
WORK="$(realpath "$1")"
ROOT="$WORK/squashfs"
IMAGE="$(realpath -m "$2")"
[[ -f "$WORK/.vigilos-owned" && -s "$ROOT/etc/vigilos-release" && ! -e "$IMAGE" ]] || { echo 'Owned root and fresh output required' >&2; exit 1; }
CONTEXTS="$ROOT/etc/selinux/targeted/contexts/files/file_contexts"
POLICY="$(find "$ROOT/etc/selinux/targeted/policy" -maxdepth 1 -type f -name 'policy.*' | sort -V | tail -1)"
[[ -f "$CONTEXTS" && -f "$POLICY" ]] || { echo 'ERROR: Target SELinux policy is required.' >&2; exit 1; }
cleanup() {
    local status=$?
    if mountpoint -q "$WORK/erofs"; then umount "$WORK/erofs"; fi
    exit "$status"
}
trap cleanup EXIT
mkdir -p "$WORK/erofs" "$(dirname "$IMAGE")"
# Validate against the target policy, not the cloud builder's smaller policy.
# Encode labels directly in EROFS: no active SELinux policy change is required.
setfiles -n -c "$POLICY" -F -r "$ROOT" "$CONTEXTS" "$ROOT/etc/passwd" "$ROOT/etc/shadow" "$ROOT/usr/bin/sddm"
EROFS_LEVEL="${VIGIL_EROFS_LEVEL:-6}"
[[ "$EROFS_LEVEL" =~ ^[1-9]$ ]] || { echo 'EROFS compression level must be1–9' >&2; exit 1; }
printf 'Packing EROFS: zstd level%s,64KiB clusters,four workers\n' "$EROFS_LEVEL"
mkfs.erofs --quiet -zzstd,"$EROFS_LEVEL" -C65536 --workers=4 --mount-point=/ --file-contexts="$CONTEXTS" "$IMAGE" "$ROOT"
mount -o loop,ro "$IMAGE" "$WORK/erofs"
python3 "$REPO_DIR/scripts/verify-root-labels.py" "$WORK/erofs"
umount "$WORK/erofs"
