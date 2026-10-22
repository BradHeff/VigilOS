#!/usr/bin/env bash
# Operates only on the prepared root inside the disposable builder.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$REPO_DIR/scripts/lib/require-builder.sh"
vigilos_require_builder
ROOT="$(realpath "$1")"
[[ ( "$ROOT" == /build/work/vigilos-branding.*/squashfs || "$ROOT" == /var/tmp/vigilos-branding.*/squashfs ) && -f "$(dirname "$ROOT")/.vigilos-owned" ]] || {
    echo 'Owned prepared image root required' >&2; exit 1;
}
# Public Brave stable keys are vendored from the vendor's HTTPS signing-keys page.
# Never disable upstream RPM verification or import anything into the host RPM DB.
printf '%s  %s\n' 'bf978bd03e49f6006568d99f620763bf43a6455f6209dff791f52ebc6239f738' "$REPO_DIR/branding/repos/pki/brave-core.asc" | sha256sum -c -
install -Dm0644 "$REPO_DIR/branding/repos/pki/brave-core.asc" "$ROOT/etc/pki/rpm-gpg/RPM-GPG-KEY-brave-release"
install -Dm0644 "$REPO_DIR/branding/repos/brave-browser.repo" "$ROOT/etc/yum.repos.d/brave-browser.repo"
chroot "$ROOT" rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-brave-release
chroot "$ROOT" dnf -y --releasever=44 install brave-browser libreoffice \
    nodejs24 nodejs24-bin nodejs24-npm nodejs24-npm-bin python3 flatpak
install -Dm0644 "$REPO_DIR/branding/repos/brave-browser.repo" "$ROOT/etc/yum.repos.d/brave-browser.repo"
# Preserve unrelated dependencies and fail if a required dependency prevents removal.
chroot "$ROOT" dnf -y --releasever=44 --setopt=clean_requirements_on_remove=False remove firefox fedora-bookmarks mediawriter
for omitted in firefox mediawriter; do
    ! chroot "$ROOT" rpm -q "$omitted"
done
chroot "$ROOT" rpm -q brave-browser libreoffice-core libreoffice-writer libreoffice-calc libreoffice-impress \
    nodejs24 nodejs24-bin nodejs24-npm nodejs24-npm-bin python3 flatpak
chroot "$ROOT" node --version
chroot "$ROOT" npm --version
chroot "$ROOT" python3 --version
chroot "$ROOT" flatpak --version
install -Dm0755 "$REPO_DIR/scripts/runtime/vigilos-anaconda-browser" "$ROOT/usr/local/libexec/vigilos-anaconda-browser"
