#!/usr/bin/env bash
set -euo pipefail
# Compatibility entry point: no disk-writing or sync step.
[[ $# -eq 0 ]] || { echo 'ERROR: USB/device arguments are unsupported.' >&2; exit 1; }
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$REPO_DIR/scripts/build-and-brand.sh"
