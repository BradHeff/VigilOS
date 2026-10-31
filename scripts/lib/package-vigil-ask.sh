#!/usr/bin/env bash
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$REPO_DIR/scripts/lib/require-builder.sh"
vigilos_require_builder
ROOT="$(realpath "$1")"
WORK="$(realpath "$2")"
[[ -f "$WORK/.vigilos-owned" && "$ROOT" == "$WORK/squashfs" ]] || exit 2
RPM="$WORK/rpmbuild-vigil-ask"
KEY="$REPO_DIR/branding/repos/pki/claude-code.asc"
printf '%s  %s\n' bd70a5e4a268002704024ceba7f8446024114e94f3f0bdd11c23a9e592be81c6 "$KEY" | sha256sum -c -
mkdir -p "$RPM"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
tar -C "$REPO_DIR" --exclude=vigil-ask/tests --exclude=__pycache__ -cf - vigil-ask | tar -C "$RPM/SOURCES" -xf -
install -m0644 "$REPO_DIR/branding/logos/source/vigil-mark.svg" "$RPM/SOURCES/org.vigilos.Ask.svg"
install -m0644 "$REPO_DIR/branding/repos/claude-code.repo" "$KEY" "$RPM/SOURCES/"
rpmbuild --define "_topdir $RPM" -bb "$REPO_DIR/vigil-ask/vigil-ask.spec"
PACKAGE="$(find "$RPM/RPMS" -name 'vigil-ask-*.noarch.rpm' -type f)"
[[ -n "$PACKAGE" && "$PACKAGE" != *$'\n'* ]] || { echo 'ERROR: Exactly one vigil-ask RPM required.' >&2; exit 1; }
cp "$PACKAGE" "$ROOT/tmp/vigil-ask.rpm"
chroot "$ROOT" dnf -y --releasever=44 install /tmp/vigil-ask.rpm
rm -f "$ROOT/tmp/vigil-ask.rpm"
! chroot "$ROOT" rpm -q claude-code >/dev/null || { echo 'ERROR: Claude Code must not be in the image.' >&2; exit 1; }
grep -qx 'enabled=0' "$ROOT/etc/yum.repos.d/claude-code.repo" || { echo 'ERROR: The Claude Code repository must ship off.' >&2; exit 1; }
[[ ! -e "$ROOT/etc/vigil-ask/disabled" ]] || { echo 'ERROR: VIGIL Ask must ship turned on.' >&2; exit 1; }
CHECK=/tmp/vigil-ask-check
install -d -m0700 "$ROOT$CHECK"
STATE="$(chroot "$ROOT" env -i HOME="$CHECK" XDG_RUNTIME_DIR="$CHECK" PATH=/usr/bin:/usr/sbin vigil-ask status)"
chroot "$ROOT" env -i HOME="$CHECK" /usr/bin/python3 -I -B -c 'import sys; sys.path.insert(0, "/usr/share/vigil-ask"); import vigil_ask.window'
rm -rf "${ROOT:?}$CHECK"
[[ "$STATE" == missing ]] || { echo "ERROR: VIGIL Ask reports $STATE in an image without Claude Code." >&2; exit 1; }
chroot "$ROOT" rpm -V vigil-ask
echo "$(chroot "$ROOT" rpm -q vigil-ask) installed in the image, without Claude Code"
