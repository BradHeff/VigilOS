#!/usr/bin/env bash
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO_DIR/scripts/lib/require-builder.sh"
vigilos_require_builder
[[ $# -eq 1 ]] || { echo 'Usage: prepare-brand-assets.sh <owned-work-directory>/branding' >&2; exit 1; }
DEST="$(realpath "$1")"
[[ -f "$(dirname "$DEST")/.vigilos-owned" ]] || { echo 'ERROR: Raster generation requires a fresh marked build work directory.' >&2; exit 1; }
SVG_DIR="$DEST/logos/source"
[[ -s "$SVG_DIR/vigil-mark.svg" && -s "$SVG_DIR/vigil-wordmark-on-dark.svg" ]] || { echo 'ERROR: Clean vector brand sources are required.' >&2; exit 1; }
MAGICK="$(command -v magick || command -v convert)"
render() {
    local svg="$1" bounds="$2" out="$3"
    # Render vector geometry above the target resolution, then fit with transparent padding.
    "$MAGICK" -background none -density 1200 "$svg" -resize "$bounds" -gravity center -extent "$bounds" "PNG32:$out"
}
render "$SVG_DIR/vigil-mark.svg" 980x980 "$DEST/logos/vigilos-logo.png"
render "$SVG_DIR/vigil-wordmark-on-dark.svg" 1029x220 "$DEST/logos/vigilos-logo-full.png"
render "$SVG_DIR/vigil-wordmark-on-dark.svg" 149x43 "$DEST/logos/vigilos-watermark.png"
render "$SVG_DIR/vigil-mark.svg" 128x128 "$DEST/logos/vigilos-watermark-128.png"
for size in 16 24 32 48 64 128 256 512; do
    render "$SVG_DIR/vigil-mark.svg" "${size}x${size}" "$DEST/logos/vigilos-icon-$size.png"
done
render "$SVG_DIR/vigil-mark.svg" 112x112 "$DEST/grub/vigilos/logo.png"

# GRUB's PNG decoder requires8-bit channels. Preserve alpha rather than
# flattening to an opaque black rectangle; source artwork remains untouched.
for png in "$DEST/grub/vigilos/"*.png; do
    [[ -f "$png" ]] || continue
    "$MAGICK" "$png" -depth 8 "PNG32:$png.vigil-rgba.png"
    mv "$png.vigil-rgba.png" "$png"
done
python3 - "$DEST/grub/vigilos" <<'PNG_VERIFY'
import pathlib,sys
for p in pathlib.Path(sys.argv[1]).glob('*.png'):
    header=p.read_bytes()[:29]
    if header[:8] != b'\x89PNG\r\n\x1a\n' or header[24:26] != bytes([8,6]):
        raise SystemExit(f'GRUB requires8-bit RGBA PNG: {p}')
    print(f'GRUB PNG verified: {p.name}:8-bit RGBA')
PNG_VERIFY
