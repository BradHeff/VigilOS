#!/usr/bin/env bash
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$REPO_DIR/scripts/lib/require-builder.sh"
vigilos_require_builder
STAGE="$REPO_DIR/vpm"
if [[ ! -f "$STAGE/PROVENANCE.json" ]]; then
    echo 'VpM was not staged for this build; the image has no vpm package.'
    exit 0
fi
ROOTFS="$(realpath "$1")"
WORK="$(realpath "$2")/rpmbuild-vpm"
mkdir -p "$WORK"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
FIELDS="$(python3 - "$STAGE" <<'PY'
import hashlib,json,sys
from pathlib import Path
stage=Path(sys.argv[1])
record=json.loads((stage/'PROVENANCE.json').read_text())
for name,digest in record['files'].items():
    with (stage/name).open('rb') as stream:
        if hashlib.file_digest(stream,'sha256').hexdigest()!=digest:
            raise SystemExit(f'ERROR: staged VpM file changed: {name}')
print(record['version'],record['release'])
PY
)"
read -r VERSION RELEASE <<<"$FIELDS"
[[ "$VERSION" =~ ^[0-9]+(\.[0-9]+)*$ && "$RELEASE" =~ ^[0-9]+\.git[0-9a-f]+$ ]] || { echo 'ERROR: Bad VpM version.' >&2; exit 1; }
mkdir -p "$WORK/SOURCES/vpm"
cp -a "$STAGE/." "$WORK/SOURCES/vpm/"
cat > "$WORK/SOURCES/vpm-profile.sh" <<'PROFILE'
# Programs installed by VpM come after the system's own.
case ":$PATH:" in *:/opt/vpm/bin:*) ;; *) PATH="$PATH:/opt/vpm/bin" ;; esac
PROFILE
cat > "$WORK/SPECS/vpm.spec" <<SPEC
Name: vpm
Version: $VERSION
Release: $RELEASE%{?dist}
SPEC
cat >> "$WORK/SPECS/vpm.spec" <<'SPEC'
Summary: Package manager for .vpm packages, installed beside RPM under /opt/vpm
License: LicenseRef-VIGIL-Personal-Build
ExclusiveArch: x86_64
Requires: bash coreutils tar curl rpm systemd libselinux-utils sqlite-libs
%global debug_package %{nil}
%global _build_id_links none
%global __os_install_post %{nil}
%description
VpM builds, signs, verifies, installs and removes .vpm packages. Their files
live under /opt/vpm, and RPM and DNF keep managing the rest of the system.
Changing the running system stays switched off until an administrator creates
/etc/vpm/allow-running-system. The binaries were built and tested on the build
host; /usr/share/vpm/PROVENANCE.json records the commit and checksums.
%install
src=%{_sourcedir}/vpm
install -Dpm0755 $src/bin/vpm %{buildroot}%{_bindir}/vpm
install -Dpm0755 $src/bin/vpm-build %{buildroot}%{_bindir}/vpm-build
install -Dpm0644 $src/man/vpm.8 %{buildroot}%{_mandir}/man8/vpm.8
install -Dpm0644 $src/man/vpm-build.1 %{buildroot}%{_mandir}/man1/vpm-build.1
install -Dpm0644 -t %{buildroot}%{_docdir}/vpm $src/doc/README.md $src/doc/FORMAT.md $src/doc/SIGNING.md
install -Dpm0644 -t %{buildroot}/usr/share/vpm/examples/hello $src/doc/examples/hello/*
install -Dpm0644 $src/PROVENANCE.json %{buildroot}/usr/share/vpm/PROVENANCE.json
install -Dpm0644 %{_sourcedir}/vpm-profile.sh %{buildroot}/etc/profile.d/vpm.sh
install -d -m0755 %{buildroot}/etc/vpm/keys/trusted %{buildroot}/etc/vpm/keys/revoked
install -d -m0755 %{buildroot}/usr/share/vpm/keys/trusted %{buildroot}/usr/share/vpm/keys/revoked
install -d -m0755 %{buildroot}/var/lib/vpm %{buildroot}/opt/vpm
%files
%{_bindir}/vpm
%{_bindir}/vpm-build
%{_mandir}/man8/vpm.8
%{_mandir}/man1/vpm-build.1
%doc %{_docdir}/vpm
/usr/share/vpm
%config(noreplace) /etc/profile.d/vpm.sh
%dir /etc/vpm
%dir /etc/vpm/keys
%dir /etc/vpm/keys/trusted
%dir /etc/vpm/keys/revoked
%dir /var/lib/vpm
%dir /opt/vpm
SPEC
rpmbuild --define "_topdir $WORK" -bb "$WORK/SPECS/vpm.spec"
PACKAGE="$(find "$WORK/RPMS" -name 'vpm-*.rpm' -type f | head -1)"
cp "$PACKAGE" "$ROOTFS/tmp/vpm.rpm"
chroot "$ROOTFS" dnf -y --releasever=44 install /tmp/vpm.rpm
rm -f "$ROOTFS/tmp/vpm.rpm"
chroot "$ROOTFS" rpm -V vpm
for name in vpm vpm-build; do
    expected="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["files"]["bin/"+sys.argv[2]])' "$STAGE/PROVENANCE.json" "$name")"
    [[ "$(sha256sum "$ROOTFS/usr/bin/$name" | cut -d' ' -f1)" == "$expected" ]] || { echo "ERROR: /usr/bin/$name differs from the tested build." >&2; exit 1; }
done
[[ "$(chroot "$ROOTFS" vpm --version)" == "vpm $VERSION" ]] || { echo 'ERROR: vpm does not run in the image.' >&2; exit 1; }
[[ ! -e "$ROOTFS/etc/vpm/allow-running-system" ]] || { echo 'ERROR: The running-system switch must ship off.' >&2; exit 1; }
echo "VpM $VERSION-$RELEASE installed in the image"
