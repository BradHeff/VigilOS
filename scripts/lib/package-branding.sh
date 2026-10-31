#!/usr/bin/env bash
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$REPO_DIR/scripts/lib/require-builder.sh"
vigilos_require_builder
source "$REPO_DIR/scripts/lib/product-version.sh"
ROOTFS="$(realpath "$1")"
WORK="$(realpath "$2")/rpmbuild"
mkdir -p "$WORK"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
bash "$REPO_DIR/scripts/lib/package-release-common.sh" "$ROOTFS" "$WORK"
COMMON="$(find "$WORK/RPMS" -name 'vigilos-release-common-*.rpm' -type f | head -1)"
cp "$COMMON" "$ROOTFS/tmp/vigilos-release-common.rpm"
mkdir -p "$WORK/SOURCES/project-licenses"
cp "$REPO_DIR/LICENSE" "$REPO_DIR/LICENSES/"* "$WORK/SOURCES/project-licenses/"
cp "$ROOTFS/usr/lib/os-release" "$WORK/SOURCES/os-release"
cp "$ROOTFS/etc/vigilos-release" "$WORK/SOURCES/vigilos-release"
cp "$ROOTFS/.buildstamp" "$WORK/SOURCES/buildstamp"
cp "$ROOTFS/usr/lib/vigilos/release.json" "$WORK/SOURCES/release.json"
printf '44\n' > "$WORK/SOURCES/releasever"
python3 "$REPO_DIR/scripts/lib/prepare-repository-overrides.py" "$ROOTFS" "$WORK/SOURCES/base-repositories.repo"
cat > "$WORK/SPECS/vigilos-release-identity.spec" <<'SPEC'
Name: vigilos-release-identity
Version: %{vigilos_version}
Release: 3%{?dist}
Summary: VIGIL OS identity on the Fedora 44 base
License: LicenseRef-VIGIL-Personal-Build
BuildArch: noarch
Source0: os-release
Source1: vigilos-release
Source2: releasever
Source3: buildstamp
Source4: base-repositories.repo
Source5: release.json
Requires: vigilos-release-common >= 44
Requires: vigilos-release-common < 45
Requires: fedora-repos(44)
Provides: fedora-release-identity = 44
Provides: fedora-release-variant = 44
Provides: fedora-release = 44
Provides: system-release
Provides: system-release(44)
Provides: system-release(releasever) = 44
Conflicts: fedora-release-variant
Obsoletes: fedora-release-kde-desktop < 45
Obsoletes: fedora-release-workstation < 45
Conflicts: fedora-release-identity
Obsoletes: fedora-release-identity-kde-desktop < 45
Obsoletes: fedora-release-identity-workstation < 45
%description
VIGIL OS product identity. Fedora repositories, keys, release macros, licenses,
compatibility metadata and signed boot components retain upstream provenance.
%install
install -Dpm0644 %{SOURCE0} %{buildroot}/usr/lib/os-release
install -Dpm0644 %{SOURCE1} %{buildroot}/etc/vigilos-release
install -Dpm0644 %{SOURCE2} %{buildroot}/etc/dnf/vars/releasever
install -Dpm0644 %{SOURCE3} %{buildroot}/.buildstamp
install -Dpm0644 %{SOURCE4} %{buildroot}/usr/share/dnf5/repos.override.d/50-vigilos-fedora-base.repo
install -Dpm0644 %{SOURCE5} %{buildroot}/usr/lib/vigilos/release.json
mkdir -p %{buildroot}%{_licensedir}/%{name}
cp -a %{_sourcedir}/project-licenses/. %{buildroot}%{_licensedir}/%{name}/
%files
%license %{_licensedir}/%{name}
%dir /usr/lib/vigilos
/usr/lib/vigilos/release.json
/.buildstamp
/usr/lib/os-release
/etc/vigilos-release
%config(noreplace) /etc/dnf/vars/releasever
/usr/share/dnf5/repos.override.d/50-vigilos-fedora-base.repo
SPEC
rpmbuild --define "_topdir $WORK" --define "vigilos_version $VIGIL_VERSION" -bb "$WORK/SPECS/vigilos-release-identity.spec"
IDENTITY="$(find "$WORK/RPMS" -name 'vigilos-release-identity-*.rpm' -type f | head -1)"
cp "$IDENTITY" "$ROOTFS/tmp/vigilos-release-identity.rpm"
chroot "$ROOTFS" dnf -y --releasever=44 install /tmp/vigilos-release-common.rpm /tmp/vigilos-release-identity.rpm

bash "$REPO_DIR/scripts/lib/package-wallpaper-compat.sh" "$ROOTFS" "$WORK"
WALLPAPER="$(find "$WORK/RPMS" -name 'vigilos-wallpaper-compat-*.rpm' -type f | head -1)"
cp "$WALLPAPER" "$ROOTFS/tmp/vigilos-wallpaper-compat.rpm"

PAYLOAD="$WORK/SOURCES/branding-payload"
mkdir -p "$PAYLOAD/usr/share/licenses/vigilos-branding"
cp -a "$WORK/SOURCES/project-licenses/." "$PAYLOAD/usr/share/licenses/vigilos-branding/"
PATHS=(etc/vigilos-desktop etc/skel/.config/kcm-about-distrorc etc/skel/.config/kdeglobals etc/skel/.config/mimeapps.list etc/yum.repos.d/brave-browser.repo etc/pki/rpm-gpg/RPM-GPG-KEY-brave-release usr/local/libexec/vigilos-anaconda-browser etc/skel/.config/kscreenlockerrc usr/share/color-schemes/VIGILDark.colors usr/share/plasma/desktoptheme/PurPurNight-Plasma usr/share/plasma/look-and-feel/VIGIL-Dark-Splash usr/share/plasma/look-and-feel/org.vigilos.desktop usr/local/share/plasma/look-and-feel usr/local/libexec/vigilos-configure-installed-boot usr/share/plasma/plasma-welcome/intro-customization.desktop etc/skel/.config/autostart/imsettings-start.desktop usr/local/share/applications/liveinst.desktop usr/share/cockpit/branding/vigilos usr/share/vigilos usr/share/grub/themes/vigilos usr/share/sddm/themes/vigilos usr/share/plymouth/themes/vigilos usr/share/plymouth/themes/vigilos-spinner usr/lib/dracut/modules.d/99vigilos-branding etc/anaconda/profile.d/vigilos.conf etc/sddm.conf.d/vigilos.conf usr/local/libexec/vigilos-is-live usr/local/libexec/vigilos-liveuser-setup usr/local/bin/vigilos-first-boot.sh etc/systemd/system/vigilos-first-boot.service etc/systemd/system/sddm-live-autologin.service etc/systemd/system/liveuser-setup.service etc/systemd/system/vigilos-gpu-setup.service usr/local/bin/vigilos-gpu-setup.sh usr/local/bin/vigilos-gpu-notify.sh etc/dracut.conf.d/vigilos-branding.conf)
PATHS+=(usr/share/glib-2.0/schemas/90-vigilos-dark.gschema.override usr/share/icons/Qogir-cursors usr/share/konsole/VIGILDark-Konsole.colorscheme)
if [[ ${VIGIL_DESKTOP:-kde} == kde ]]; then
    PATHS+=(etc/skel/.config/gtk-3.0 etc/skel/.config/gtk-4.0 etc/skel/.config/environment.d/gtk-flatpak.conf etc/skel/.config/plasmarc etc/skel/.config/ksplashrc etc/skel/.config/kwinrc usr/share/themes/VALYRIAN-Total-Steel usr/share/icons/Slot-Beauty-Dark-Icons usr/share/icons/Qogir-white-cursors)
fi
if [[ ${VIGIL_DESKTOP:-kde} == i3 ]]; then PATHS+=(etc/lightdm/lightdm.conf.d/50-vigilos.conf etc/systemd/system/vigilos-i3-live.service); fi

PATHS+=(usr/share/pixmaps/vigilos-logo.png usr/share/pixmaps/vigilos-start.svg usr/share/pixmaps/vigilos-watermark.png usr/share/pixmaps/vigilos-watermark-128.png)
ICON_CANDIDATES=()
for name in start-here distributor-logo vigilos-start start-here-kde start-here-kde-panel; do
    ICON_CANDIDATES+=("usr/share/icons/hicolor/scalable/apps/$name.svg")
done
for name in start-here distributor-logo; do ICON_CANDIDATES+=("usr/share/pixmaps/$name.svg"); done
for size in 16 22 24 32 48 64 96 128 256 512; do
    for name in vigilos-logo vigilos-start start-here distributor-logo start-here-kde start-here-kde-panel; do
        ICON_CANDIDATES+=("usr/share/icons/hicolor/${size}x${size}/apps/$name.png")
    done
done
for rel in "${ICON_CANDIDATES[@]}"; do
    [[ -e "$ROOTFS/$rel" ]] || continue
    if ! owner="$(chroot "$ROOTFS" rpm -qf --qf '%{NAME}' "/$rel" 2>/dev/null)"; then owner=""; fi
    case "$owner" in ''|vigilos-branding) PATHS+=("$rel") ;; esac
done
: > "$WORK/SOURCES/branding-files.list"
for rel in "${PATHS[@]}"; do
    [[ -e "$ROOTFS/$rel" ]] || continue
    mkdir -p "$PAYLOAD/$(dirname "$rel")"
    cp -a "$ROOTFS/$rel" "$PAYLOAD/$rel"

    case "$rel" in usr/share/vigilos|usr/share/plasma/look-and-feel/*|usr/local/share/plasma/look-and-feel|usr/share/sddm/themes/vigilos|usr/share/grub/themes/vigilos|usr/share/plymouth/themes/vigilos*)
        find "$PAYLOAD/$rel" -type d -exec chmod a+rx {} +
        find "$PAYLOAD/$rel" -type f -exec chmod a+r {} +
        ;;
    esac
    printf '/%s\n' "$rel" >> "$WORK/SOURCES/branding-files.list"
done
cat > "$WORK/SPECS/vigilos-branding.spec" <<'SPEC'
Name: vigilos-branding
Version: %{vigilos_version}
%if 0%{?vigilos_i3}
Release: 24%{?dist}
%else
Release: 23%{?dist}
%endif
Summary: VIGIL OS desktop and boot branding assets
License: LicenseRef-VIGIL-Personal-Build AND GPL-3.0-only AND GPL-2.0-or-later AND LGPL-2.0-or-later AND CC-BY-SA-4.0 AND LicenseRef-byrotek-Permission
BuildArch: noarch
Requires: vigilos-release-identity = %{version}
Requires: plymouth-theme-spinner
%if 0%{?vigilos_i3}
Requires: vigilos-i3-desktop
%else
Requires: plasma-welcome
%endif
Requires: grubby
Conflicts: plasma-welcome-fedora
Obsoletes: plasma-welcome-fedora <= 6.3.4-3.fc44
%description
VIGIL OS product assets and a separate spinner theme derived from upstream.
Existing upstream notices and licenses are retained in the image. These local
candidate RPMs are unsigned development artifacts and are not a public repository.
%install
cp -a %{_sourcedir}/branding-payload/. %{buildroot}/
%files -f %{_sourcedir}/branding-files.list
%license /usr/share/licenses/vigilos-branding
SPEC
rpmbuild --define "_topdir $WORK" --define "vigilos_version $VIGIL_VERSION" --define "vigilos_i3 $([[ ${VIGIL_DESKTOP:-kde} == i3 ]] && echo 1 || echo 0)" -bb "$WORK/SPECS/vigilos-branding.spec"
BRANDING="$(find "$WORK/RPMS" -name 'vigilos-branding-*.rpm' -type f | head -1)"
cp "$BRANDING" "$ROOTFS/tmp/vigilos-branding.rpm"
chroot "$ROOTFS" dnf -y --releasever=44 install /tmp/vigilos-branding.rpm /tmp/vigilos-wallpaper-compat.rpm
if [[ ${VIGIL_DESKTOP:-kde} == i3 ]]; then
    owner="$(chroot "$ROOTFS" rpm -qf --qf '%{NAME}' /etc/lightdm/lightdm-gtk-greeter.conf)"
    [[ "$owner" == lightdm-gtk ]] || { echo 'ERROR: Native greeter configuration must retain sole upstream ownership.' >&2; exit 1; }
fi
chroot "$ROOTFS" rpm -V vigilos-release-common vigilos-release-identity vigilos-branding vigilos-wallpaper-compat
chroot "$ROOTFS" rpm -qa --qf '%{NAME} %{VERSION}-%{RELEASE}.%{ARCH}\n' | sort > "$(dirname "$WORK")/package-manifest.txt"
rm -f "$ROOTFS/tmp/vigilos-release-common.rpm" "$ROOTFS/tmp/vigilos-release-identity.rpm" "$ROOTFS/tmp/vigilos-branding.rpm" "$ROOTFS/tmp/vigilos-wallpaper-compat.rpm"
