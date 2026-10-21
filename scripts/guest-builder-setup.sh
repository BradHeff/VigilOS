#!/usr/bin/env bash
set -euo pipefail
[[ "${VIGIL_BUILD_GUEST:-0}" == 1 ]] || { echo "Set VIGIL_BUILD_GUEST=1 only inside the approved disposable builder." >&2; exit 1; }
[[ $(id -u) -eq 0 ]] || { echo 'Builder setup requires guest root.' >&2; exit 1; }
systemd-detect-virt --vm --quiet
mkdir -p /build/source /build/export /build/work /build/output
exec > >(tee -a /build/export/setup.log /dev/ttyS0) 2>&1
systemd-run --unit=vigil-artifact-server --property=WorkingDirectory=/build/export /usr/bin/python3 -m http.server 8000 --bind 0.0.0.0
cp -a /mnt/source/. /build/source/
touch /etc/vigilos-disposable-builder
dnf install -y osbuild-composer weldr-client squashfs-tools xorriso rsync xz cpio ImageMagick grub2-tools grub2-tools-extra dosfstools pykickstart ShellCheck isomd5sum rpm-build mtools erofs-utils file dejavu-sans-fonts
systemctl start osbuild-composer.socket
printf 'READY\n' > /build/export/ready.txt
cat /etc/os-release
rpm -q osbuild-composer weldr-client
