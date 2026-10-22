#!/usr/bin/env bash
set -euo pipefail
exec > >(tee /build-bootstrap.log /dev/ttyS0) 2>&1
trap 'touch /build/setup-failed' ERR
systemd-detect-virt --vm --quiet
mkdir -p /build/{source,work,output,export} /mnt/source
mount -o ro /dev/disk/by-label/VIGIL_SOURCE /mnt/source
cp -a /mnt/source/. /build/source/
touch /etc/vigilos-disposable-builder
dnf -y install sudo squashfs-tools xorriso rsync xz cpio ImageMagick grub2-tools grub2-tools-extra dosfstools pykickstart ShellCheck isomd5sum rpm-build mtools erofs-utils file dejavu-sans-fonts policycoreutils policycoreutils-python-utils python3 python3-pillow
umount /mnt/source
if [[ ${VIGIL_DESKTOP:-kde} == i3 ]]; then
    VIGIL_BUILD_GUEST=1 bash /build/source/scripts/lib/build-i3-lock.sh
fi
touch /build/ready
printf 'VIGIL_BUILDER_READY\n'
