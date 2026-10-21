#!/usr/bin/env bash
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO_DIR/scripts/lib/require-builder.sh"
vigilos_require_builder
BASE="${VIGIL_BASE_ISO:-${1:-/dev/disk/by-label/Fedora-KDE-Live-44}}"
[[ -f "$BASE" || -b "$BASE" ]] || { echo 'ERROR: Attach or provide a verified official Fedora 44 KDE ISO.' >&2; exit 1; }
OUTPUT_ROOT="${VIGIL_OUTPUT_ROOT:-/build/output}"
WORK_ROOT="${VIGIL_WORK_ROOT:-/build/work}"
mkdir -p "$OUTPUT_ROOT" "$WORK_ROOT"
RUN_DIR="$(mktemp -d "$OUTPUT_ROOT/candidate.XXXXXX")"
ISO_PATH="$RUN_DIR/VIGILOS-1.2-x86_64.iso"
bash "$REPO_DIR/scripts/validate.sh" 2>&1 | tee "$RUN_DIR/validation.log"
VIGIL_WORK_ROOT="$WORK_ROOT" bash "$REPO_DIR/scripts/apply-composer-branding.sh" "$BASE" "$ISO_PATH" 2>&1 | tee "$RUN_DIR/branding.log"
sha256sum "$ISO_PATH" > "$ISO_PATH.sha256"
printf 'Candidate ISO: %s\nEvidence: %s\n' "$ISO_PATH" "$RUN_DIR"
