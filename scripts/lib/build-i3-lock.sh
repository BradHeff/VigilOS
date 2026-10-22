#!/usr/bin/env bash
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$REPO_DIR/scripts/lib/require-builder.sh"
vigilos_require_builder
ASSETS="$REPO_DIR/branding/i3"
BUILD_WORK=/build/toolchain
mkdir -p "$BUILD_WORK"
[[ ! -e "$BUILD_WORK/i3lock-source" ]] || { echo 'Refusing to overwrite an existing toolchain build'; exit 1; }
printf '%s  %s\n' 46f15cbbf339873266e014f70b5e1ec02177f0295302b615a7bd85bef40d8ad2 "$ASSETS/vendor/i3lock-color-2.13.c.5.tar.gz" | sha256sum -c -
dnf -y install gcc make autoconf automake pkgconf-pkg-config cairo-devel fontconfig-devel libev-devel libjpeg-turbo-devel libXinerama-devel libXrandr-devel libxkbcommon-devel libxkbcommon-x11-devel pam-devel xcb-util-image-devel xcb-util-xrm-devel libxcb-devel
mkdir -p "$BUILD_WORK/i3lock-source"
tar -xf "$ASSETS/vendor/i3lock-color-2.13.c.5.tar.gz" -C "$BUILD_WORK/i3lock-source" --strip-components=1
pushd "$BUILD_WORK/i3lock-source"
autoreconf -fi
mkdir build
cd build
../configure --prefix=/usr --sysconfdir=/etc --disable-sanitizers
make -j4
popd
test -x "$BUILD_WORK/i3lock-source/build/i3lock"
printf 'Pinned i3lock-color compile preflight passed\n'
