#!/usr/bin/env bash
# Replace only the Fedora KDE artwork wrapper; keep native desktop dependencies.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO_DIR/scripts/lib/require-builder.sh"
vigilos_require_builder
ROOT="$(realpath "$1")"
WORK="$(realpath "$2")"
[[ -f "$(dirname "$ROOT")/.vigilos-owned" && "$ROOT" == */squashfs ]] || exit 1
PROVIDER="$(chroot "$ROOT" rpm -q --whatprovides f44-backgrounds-kde --qf '%{NAME}\n')"
case "$PROVIDER" in f44-backgrounds-kde|vigilos-wallpaper-compat) ;; *) echo 'Unexpected wallpaper provider'; exit 1 ;; esac
BASE_EVR="$(chroot "$ROOT" rpm -q --provides "$PROVIDER" | awk '$1 == "f44-backgrounds-kde" && $2 == "=" {print $3; exit}')"
[[ "$BASE_EVR" =~ ^44\.[0-9.]+-[0-9A-Za-z._+]+$ ]] || exit 1
python3 - "$ROOT" "$WORK" <<'PY'
from pathlib import Path
import json,sys
root,work=map(Path,sys.argv[1:])
meta=json.loads((root/'usr/share/vigilos/wallpapers/VIGILOS/metadata.json').read_text())
meta['KPlugin']['Id']='F44'
(work/'SOURCES/wallpaper-compat-metadata.json').write_text(json.dumps(meta,indent=2,ensure_ascii=False)+'\n')
PY
cp "$ROOT/usr/share/licenses/f44-backgrounds-base/CC-BY-SA-4.0" "$WORK/SOURCES/wallpaper-compat-LICENSE"
cat >"$WORK/SPECS/vigilos-wallpaper-compat.spec" <<SPEC
Name: vigilos-wallpaper-compat
Version: 1.2
Release: 1%{?dist}
Summary: VIGIL OS KDE wallpaper with Fedora44 dependency compatibility
License: CC-BY-SA-4.0
BuildArch: noarch
Source0: wallpaper-compat-metadata.json
Source1: wallpaper-compat-LICENSE
Provides: f44-backgrounds-kde = $BASE_EVR
Conflicts: f44-backgrounds-kde
Obsoletes: f44-backgrounds-kde < 45
Requires: kde-filesystem
Requires: /usr/share/vigilos/wallpapers/VIGILOS/metadata.json
SPEC
cat >>"$WORK/SPECS/vigilos-wallpaper-compat.spec" <<'SPEC'
%description
Product artwork wrapper for the Fedora44 KDE dependency contract. The F44
compatibility directory and Default alias remain stable; visible artwork and
metadata are VIGIL OS. Native Fedora repositories/solver/signatures are unchanged.
Original base-art attribution and licenses remain with their upstream package.
%install
install -Dpm0644 %{SOURCE0} %{buildroot}/usr/share/wallpapers/F44/metadata.json
install -Dpm0644 %{SOURCE1} %{buildroot}%{_licensedir}/%{name}/CC-BY-SA-4.0
mkdir -p %{buildroot}/usr/share/wallpapers/F44/contents/images
ln -s /usr/share/vigilos/wallpapers/VIGILOS/contents/images/1672x941.png %{buildroot}/usr/share/wallpapers/F44/contents/images/1672x941.png
%files
%license %{_licensedir}/%{name}/CC-BY-SA-4.0
/usr/share/wallpapers/F44
SPEC
rpmbuild --define "_topdir $WORK" -bb "$WORK/SPECS/vigilos-wallpaper-compat.spec"
