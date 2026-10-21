#!/usr/bin/env bash
# Fork the installed Fedora common metadata, retaining its MIT notices/presets/macros.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO_DIR/scripts/lib/require-builder.sh"
vigilos_require_builder
ROOTFS="$(realpath "$1")"
WORK="$(realpath "$2")"
PROVIDER="$(chroot "$ROOTFS" rpm -qf --qf '%{NAME}' /etc/redhat-release)"
case "$PROVIDER" in fedora-release-common|vigilos-release-common) ;; *) echo 'Unexpected release metadata owner' >&2; exit 1 ;; esac
BASE_EVR="$(chroot "$ROOTFS" rpm -q --provides "$PROVIDER" | awk '$1 == "fedora-release-common" && $2 == "=" {print $3}')"
[[ "$BASE_EVR" =~ ^44-[0-9A-Za-z._+]+$ ]] || { echo 'Fedora44 metadata version required' >&2; exit 1; }
mkdir -p "$WORK"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
python3 - "$ROOTFS" "$WORK" "$PROVIDER" <<'PY'
import pathlib,shutil,subprocess,sys
root,work=map(pathlib.Path,sys.argv[1:3]);provider=sys.argv[3]
payload=work/'SOURCES/release-common-payload';payload.mkdir()
paths=subprocess.check_output(['chroot',str(root),'rpm','-ql',provider],text=True).splitlines()
manifest=[]
for rel in paths:
 p=pathlib.PurePosixPath(rel)
 if not p.is_absolute() or '..' in p.parts:raise SystemExit('Unsafe RPM path')
 src=root/rel.lstrip('/');dst=payload/rel.lstrip('/')
 dst.parent.mkdir(parents=True,exist_ok=True)
 if src.is_dir() and not src.is_symlink():
  dst.mkdir(exist_ok=True);shutil.copystat(src,dst);manifest.append('%dir '+rel)
 else:
  shutil.copy2(src,dst,follow_symlinks=False)
  prefix='%license ' if rel.startswith('/usr/share/licenses/') else ''
  if rel.startswith('/etc/') and not src.is_symlink():prefix='%config(noreplace) '
  manifest.append(prefix+rel)
for name in ['redhat-release','system-release']:
 p=payload/'etc'/name;p.unlink();p.symlink_to('vigilos-release')
(work/'SOURCES/release-common-files.list').write_text('\n'.join(manifest)+'\n')
PY
cat >"$WORK/SPECS/vigilos-release-common.spec" <<SPEC
Name: vigilos-release-common
Version: 44
Release: 1%{?dist}
Summary: Fedora44 compatibility metadata and VIGIL OS legacy identity links
License: MIT
BuildArch: noarch
Provides: fedora-release-common = $BASE_EVR
Conflicts: fedora-release-common
Obsoletes: fedora-release-common < 45
SPEC
chroot "$ROOTFS" rpm -q --provides "$PROVIDER" | awk '/^rpm_macro\(/ {print "Provides: " $0}' >>"$WORK/SPECS/vigilos-release-common.spec"
cat >>"$WORK/SPECS/vigilos-release-common.spec" <<'SPEC'
%description
VIGIL OS owns the legacy system identity links. Fedora44 repository compatibility,
RPM macros, presets, CPE/SWID provenance and upstream MIT/legal notices are retained
from the official Fedora release-common package. Product identity is supplied by
the separately required VIGIL OS identity package.
%install
cp -a %{_sourcedir}/release-common-payload/. %{buildroot}/
%files -f %{_sourcedir}/release-common-files.list
SPEC
rpmbuild --define "_topdir $WORK" -bb "$WORK/SPECS/vigilos-release-common.spec"
