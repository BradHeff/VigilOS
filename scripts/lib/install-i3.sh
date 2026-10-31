#!/usr/bin/env bash
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$REPO_DIR/scripts/lib/require-builder.sh"
vigilos_require_builder
source "$REPO_DIR/scripts/lib/product-version.sh"
ROOT=$(realpath "$1")
WORK=$(realpath "$2")
[[ -f "$WORK/.vigilos-owned" && "$ROOT" == "$WORK/squashfs" ]] || exit 2
ASSETS="$REPO_DIR/branding/i3"
printf '%s  %s\n' 46f15cbbf339873266e014f70b5e1ec02177f0295302b615a7bd85bef40d8ad2 "$ASSETS/vendor/i3lock-color-2.13.c.5.tar.gz" 80b189fc9ce2e0a56e33be642875f5c3fb53647465f8024a541621307a6a290f "$ASSETS/vendor/greenclip-v4.2" | sha256sum -c -
chroot "$ROOT" dnf -y --releasever=44 install i3 i3lock lightdm lightdm-gtk polybar rofi xset lxpolkit gtk-murrine-engine upower alacritty xclip feh xss-lock dunst thunar mousepad network-manager-applet xdg-desktop-portal xdg-desktop-portal-gtk dbus-tools qt6-qtbase-gui gnome-keyring-pam brightnessctl xinput xrandr xorg-x11-xinit open-sans-fonts xorg-x11-server-Xorg xorg-x11-drv-libinput pipewire-pulseaudio pulseaudio-utils pavucontrol papirus-icon-theme breeze-icon-theme jq slop ffmpeg-free libnotify unzip 7zip

LOCK_BINARY=/build/toolchain/i3lock-source/build/i3lock
[[ -x "$LOCK_BINARY" ]] || bash "$REPO_DIR/scripts/lib/build-i3-lock.sh"
RPM="$WORK/i3-rpm"
mkdir -p "$RPM"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
PAYLOAD="$RPM/SOURCES/payload"
mkdir -p "$PAYLOAD/usr/share/xsessions" "$PAYLOAD/etc/dnf/protected.d" "$PAYLOAD/etc/skel" "$PAYLOAD/usr/local/bin" "$PAYLOAD/usr/bin" "$PAYLOAD/usr/share/fonts/vigilos-i3" "$PAYLOAD/usr/share/licenses/vigilos-i3-desktop"
printf "i3\nlightdm\n" > "$PAYLOAD/etc/dnf/protected.d/vigilos-i3.conf"
cat > "$PAYLOAD/usr/share/xsessions/vigilos-i3.desktop" <<'SESSION'
[Desktop Entry]
Name=VIGIL OS i3
Comment=VIGIL i3 desktop with managed idle locking
Exec=/usr/local/bin/vigil-i3-run
TryExec=/usr/bin/i3
Type=XSession
X-LightDM-DesktopName=i3
DesktopNames=i3
SESSION
cp -a "$ASSETS/skel/." "$PAYLOAD/etc/skel/"
install -Dm0644 "$ASSETS/session/vigilos-i3-session.target" "$PAYLOAD/usr/lib/systemd/user/vigilos-i3-session.target"
install -Dm0644 "$ASSETS/session/i3-portals.conf" "$PAYLOAD/usr/share/xdg-desktop-portal/i3-portals.conf"
cp -a "$ASSETS/bin/." "$PAYLOAD/usr/local/bin/"
cp -a "$ASSETS/icons" "$PAYLOAD/usr/local/bin/"
install -m0755 "$LOCK_BINARY" "$PAYLOAD/usr/bin/i3lock-color"
install -m0755 "$ASSETS/vendor/greenclip-v4.2" "$PAYLOAD/usr/local/bin/greenclip"
cp "$ASSETS/fonts/"*.ttf "$PAYLOAD/usr/share/fonts/vigilos-i3/"
chmod 0644 "$PAYLOAD/usr/share/fonts/vigilos-i3/"*.ttf
cp "$ASSETS/fonts/LICENSE.md" "$ASSETS/fonts/Feather-LICENSE" "$ASSETS/vendor/greenclip-LICENSE" "$ASSETS/rofi-LICENSE" "/build/toolchain/i3lock-source/LICENSE" "$PAYLOAD/usr/share/licenses/vigilos-i3-desktop/"
cp "$REPO_DIR/LICENSE" "$REPO_DIR/LICENSES/"* "$PAYLOAD/usr/share/licenses/vigilos-i3-desktop/"
find "$PAYLOAD" -type d -exec chmod 0755 {} +
chmod 0644 "$PAYLOAD/etc/skel/.bashrc.d/50-vigilos-i3.sh" "$PAYLOAD/etc/skel/.git-prompt.bash"
cp -a "$ASSETS/appearance/themes" "$PAYLOAD/usr/share/"
cp -a "$ASSETS/appearance/icons" "$PAYLOAD/usr/share/"
tar -C "$PAYLOAD" -cf "$RPM/SOURCES/payload.tar" .
cat > "$RPM/SPECS/i3.spec" <<'SPEC'
Name: vigilos-i3-desktop
Version: %{vigilos_version}
Release: 5%{?dist}
Summary: VIGIL OS i3 desktop, user theme and pinned upstream utilities
License: LicenseRef-VIGIL-Personal-Build AND GPL-3.0-only AND MIT AND BSD-3-Clause AND OFL-1.1
Source0: payload.tar
Requires: i3, i3lock, lightdm, lightdm-gtk, polybar, rofi, xset, lxpolkit, alacritty, xclip, breeze-icon-theme, feh, xss-lock, dunst, thunar, brightnessctl, xinput
Requires: dbus-tools, qt6-qtbase-gui, xdg-desktop-portal, xdg-desktop-portal-gtk
Requires: gtk-murrine-engine
Provides: i3lock-color = 2.13.c.5
%description
User-requested portable i3 desktop. Greenclip4.2 and i3lock-color2.13.c.5 are
pinned upstream releases; Fedora PAM authentication and SELinux remain active.
%install
mkdir -p %{buildroot}
tar -xf %{SOURCE0} -C %{buildroot}
%files
%defattr(-,root,root,-)
%config(noreplace) /etc/dnf/protected.d/vigilos-i3.conf
%config(noreplace) /etc/skel/.bashrc.d/50-vigilos-i3.sh
%config(noreplace) /etc/skel/.git-prompt.bash
%config(noreplace) /etc/skel/.Xresources
%config(noreplace) /etc/skel/.gtkrc-2.0
/etc/skel/.config/i3
/etc/skel/.config/polybar
/etc/skel/.config/rofi
/etc/skel/.config/alacritty
/etc/skel/.config/dunst
/etc/skel/.config/gtk-3.0
/etc/skel/.config/gtk-4.0
/usr/bin/i3lock-color
/usr/local/bin/*
/usr/share/fonts/vigilos-i3
/usr/share/xsessions/vigilos-i3.desktop
/usr/lib/systemd/user/vigilos-i3-session.target
/usr/share/xdg-desktop-portal/i3-portals.conf
/usr/share/themes/VALYRIAN-Total-Steel
/usr/share/icons/Slot-Beauty-Dark-Icons
/usr/share/icons/Qogir-white-cursors
%license /usr/share/licenses/vigilos-i3-desktop
SPEC
rpmbuild --define "_topdir $RPM" --define "vigilos_version $VIGIL_VERSION" -bb "$RPM/SPECS/i3.spec"

install -Dm0644 "$PAYLOAD/etc/dnf/protected.d/vigilos-i3.conf" "$ROOT/etc/dnf/protected.d/vigilos-i3.conf"

for guard in "$ROOT/etc/dnf/protected.d/"*.conf; do
    [[ -f "$guard" ]] || continue
    if [[ $(sed '/^[[:space:]]*#/d;/^[[:space:]]*$/d' "$guard") == plasma-desktop ]]; then
        printf 'Replacing offline KDE-specific desktop protection: %s\n' "$guard"
        rm "$guard"
    fi
done
chroot "$ROOT" dnf -y remove --noautoremove plasma-desktop plasma-workspace plasma-welcome sddm sddm-kcm sddm-wayland-plasma
cp "$RPM"/RPMS/x86_64/*.rpm "$ROOT/tmp/"
I3_RPM="$(find "$RPM/RPMS" -name "vigilos-i3-desktop-${VIGIL_VERSION}-*.rpm" -type f)"
[[ -n "$I3_RPM" && "$I3_RPM" != *$'\n'* ]] || { echo 'ERROR: Exactly one version-matched i3 RPM required.' >&2; exit 1; }
chroot "$ROOT" dnf -y install "/tmp/$(basename "$I3_RPM")"
chroot "$ROOT" rpm -q i3 lightdm anaconda-live anaconda-webui brave-browser libreoffice-core nodejs24 python3 flatpak vigilos-i3-desktop
chroot "$ROOT" dnf check
mkdir -p "$ROOT/etc/X11/xinit/Xsession.d" "$ROOT/etc/accountsservice/user-templates" "$ROOT/var/lib/AccountsService/users"
mkdir -p "$ROOT/etc/lightdm/lightdm.conf.d"
cat > "$ROOT/etc/lightdm/lightdm.conf.d/50-vigilos.conf" <<'CONF'
[Seat:*]
user-session=vigilos-i3
greeter-session=lightdm-gtk-greeter
CONF

cat > "$ROOT/etc/lightdm/lightdm-gtk-greeter.conf" <<'CONF'
[greeter]
background=/usr/share/vigilos/wallpapers/VIGILOS/contents/images/3840x2160.png
user-background=false
theme-name=VALYRIAN-Total-Steel
icon-theme-name=Slot-Beauty-Dark-Icons
cursor-theme-name=Qogir-white-cursors
cursor-theme-size=24
font-name=Iosevka Nerd Font 11
CONF
cat > "$ROOT/etc/systemd/system/vigilos-i3-live.service" <<'UNIT'
[Unit]
Description=VIGIL i3 live-only login
After=local-fs.target liveuser-setup.service
Before=lightdm.service display-manager.service
[Service]
Type=oneshot
ExecCondition=/usr/local/libexec/vigilos-is-live
ExecStart=/usr/bin/bash -c 'printf "[Seat:*]\nautologin-user=liveuser\nautologin-session=vigilos-i3\n" > /etc/lightdm/lightdm.conf.d/99-vigilos-live.conf'
RemainAfterExit=yes
[Install]
WantedBy=graphical.target
UNIT
rm -f "$ROOT/etc/systemd/system/display-manager.service"
chroot "$ROOT" systemctl disable sddm-live-autologin.service || true
chroot "$ROOT" systemctl enable lightdm.service vigilos-i3-live.service
printf 'PREFERRED=/usr/local/bin/vigil-i3-run\n' > "$ROOT/etc/X11/xinit/Xsession.d/50-default-session"
printf 'PREFERRED=/usr/local/bin/vigil-i3-run\n' > "$ROOT/etc/sysconfig/desktop"
for home in "$ROOT/etc/skel" "$ROOT/home/liveuser"; do
    printf '[Desktop]\nSession=vigilos-i3\n' > "$home/.dmrc"
done
printf '[User]\nSession=vigilos-i3\nXSession=vigilos-i3\nIcon=/usr/share/pixmaps/vigilos-logo.png\nSystemAccount=false\n' > "$ROOT/var/lib/AccountsService/users/liveuser"
for template in "$ROOT/etc/accountsservice/user-templates/standard" "$ROOT/var/lib/AccountsService/users/default"; do
    printf '[User]\nSession=vigilos-i3\nXSession=vigilos-i3\nSystemAccount=false\n' > "$template"
done
for file in kdeglobals kwinrc plasmarc plasmashellrc plasma-org.kde.plasma.desktop-appletsrc plasma-welcomerc ksplashrc konsolerc; do
    rm -f "$ROOT/etc/skel/.config/$file" "$ROOT/home/liveuser/.config/$file"
done
for home in "$ROOT/etc/skel" "$ROOT/home/liveuser"; do

    rm -f "$home/.config/environment.d/gtk-flatpak.conf" "$home/.local/bin/hfetch"
    rm -rf "$home/.local/share/konsole"
done
cp -a "$ROOT/etc/skel/." "$ROOT/home/liveuser/"
chroot "$ROOT" chown -R liveuser:liveuser /home/liveuser
chroot "$ROOT" fc-cache -f
mkdir -p "$ROOT/tmp/vigil-i3-check"
chroot "$ROOT" env XDG_RUNTIME_DIR=/tmp/vigil-i3-check i3 -C -c /etc/skel/.config/i3/config
rm -rf "$ROOT/tmp/vigil-i3-check"
chroot "$ROOT" rpm -V vigilos-i3-desktop bash
printf 'i3 desktop installed and verified\n'
