# ============================================
# VIGILOS KDE Plasma - Fedora 44 Base
# ============================================

# Language and Locale
lang en_AU.UTF-8
keyboard us
timezone Australia/Adelaide --utc

# Security
selinux --enforcing
firewall --enabled --service=mdns,kdeconnect

# Network
network --bootproto=dhcp --device=link --activate --hostname=vigilos

# Bootloader
# Blacklist nouveau: it has no working KMS on NVIDIA Ada Lovelace / RTX 40xx
# (e.g. GTX/RTX 4080 = AD103) and boots to a black screen with only a cursor.
# The akmod-nvidia driver installed at first boot takes over once present.
bootloader --timeout=5 --append="rd.driver.blacklist=nouveau modprobe.blacklist=nouveau nouveau.modeset=0"

# Disk partitioning (16GB for KDE + apps)
zerombr
clearpart --all --initlabel
reqpart --add-boot
part / --fstype="ext4" --size=16384

# Live account is configured by the guarded shared branding phase.

# Root stays locked; the installer creates the installed user.
rootpw --lock

# Repositories
url --mirrorlist=https://mirrors.fedoraproject.org/mirrorlist?repo=fedora-44&arch=x86_64
repo --name=updates --mirrorlist=https://mirrors.fedoraproject.org/mirrorlist?repo=updates-released-f44&arch=x86_64

# ============================================
# PACKAGES
# ============================================
%packages

# Live image essentials
dracut-live
livesys-scripts

# KDE Plasma Desktop
@kde-desktop
@kde-apps
@kde-media
@sound-and-video
plasma-workspace-wayland
plasma-workspace-wayland
plasma-systemmonitor
plasma-discover
xdg-desktop-portal-kde
xdg-desktop-portal
anaconda-webui
webkit2gtk4.1
dbus-x11
xorg-x11-server-Xorg
xorg-x11-drv-libinput
xorg-x11-xinit

# Network
NetworkManager
NetworkManager-wifi
NetworkManager-bluetooth

# Fonts
google-noto-sans-fonts
google-noto-serif-fonts
dejavu-sans-fonts
dejavu-serif-fonts
liberation-fonts-all

# Printing
cups
cups-filters

# KDE Connect
kdeconnectd

# Native Applications (Brave is added by the guarded shared branding phase)
-firefox
remmina
remmina-plugins-rdp
remmina-plugins-vnc
libreoffice
nodejs24
nodejs24-bin
nodejs24-npm
nodejs24-npm-bin
python3

# Flatpak support
flatpak

# System utilities
fastfetch
htop
git
vim-enhanced
wget2
curl

# Multimedia codecs (base Fedora)
gstreamer1-plugins-bad-free
gstreamer1-plugins-good

# Firmware
linux-firmware
iwlwifi-dvm-firmware
iwlwifi-mvm-firmware

# Plymouth theming
plymouth-theme-spinner
plymouth-plugin-script

# Remove unwanted Fedora branding
-fedora-bookmarks
-fedora-chromium-config

%end

# ============================================
# POST-INSTALL SCRIPTS
# ============================================
%post --log=/root/vigilos-post.log

# ----------------------
# OS Release Branding
# ----------------------
# Write canonical /usr/lib/os-release (fedora-release ships it there) so no tool
# reports "Fedora"; /etc/os-release becomes a symlink to it.
cat > /usr/lib/os-release << 'EOF'
NAME="VIGIL OS"
VERSION="1.2 (Loopback)"
ID=vigilos
ID_LIKE=fedora
VERSION_ID=1.2
VERSION_CODENAME=loopback
PRETTY_NAME="VIGIL OS 1.2 (Loopback)"
ANSI_COLOR="0;38;2;129;212;250"
LOGO=vigilos-logo
CPE_NAME="cpe:/o:vigilos:vigilos:1.2"
VARIANT="KDE Plasma"
VARIANT_ID=kde
HOME_URL="https://vigilglm.ai"
DOCUMENTATION_URL="https://docs.vigilglm.ai"
SUPPORT_URL="https://support.vigilglm.ai"
BUG_REPORT_URL="https://github.com/vigilglm/vigilos/issues"
PRIVACY_POLICY_URL="https://vigilglm.ai/privacy"
EOF
ln -sf ../usr/lib/os-release /etc/os-release

cat > /etc/system-release << 'EOF'
VIGIL OS release 1.2 (Loopback)
EOF

cat > /etc/vigilos-release << 'EOF'
VIGIL OS release 1.2 (Loopback)
EOF

# Console login banners (otherwise inherited from fedora-release / setup).
printf 'VIGIL OS 1.2 (Loopback) \\r (\\l)\n\n' > /etc/issue
printf 'VIGIL OS 1.2 (Loopback)\n' > /etc/issue.net

# ----------------------
# Anaconda installer profile (bootloader-install fix)
# ----------------------
# Rebranding ID=vigilos stops Anaconda from matching a stock profile in
# /etc/anaconda/profile.d/, so it falls back to efi_dir="default" and the
# bootloader step's gen_grub_cfgstub fails (it writes to /boot/efi/EFI/default,
# but shim/grub2-efi install to EFI/fedora). Ship an vigilos profile that
# inherits the fedora profile -> efi_dir=fedora and GRUB installs cleanly.
mkdir -p /etc/anaconda/profile.d
cat > /etc/anaconda/profile.d/vigilos.conf << 'EOF'
[Profile]
profile_id = vigilos
base_profile = fedora

[Profile Detection]
os_id = vigilos
[User Interface]
webui_web_engine = /usr/local/libexec/vigilos-anaconda-browser
EOF

# ----------------------
# Flatpak Setup - Repo only (installs at first boot)
# ----------------------
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

# ----------------------
# First Boot Flatpak Installer
# ----------------------
cat > /usr/local/bin/vigilos-first-boot.sh << 'FIRSTBOOT'
#!/bin/bash
MARKER="/var/lib/vigilos-first-boot-done"
[ -f "$MARKER" ] && exit 0

# Wait for network
sleep 15

# Official-only first pass: no third-party repositories, drivers, or Flatpaks.
# Optional driver setup will be separately authorized and validated.

touch "$MARKER"
FIRSTBOOT

chmod +x /usr/local/bin/vigilos-first-boot.sh

cat > /etc/systemd/system/vigilos-first-boot.service << 'SERVICEUNIT'
[Unit]
Description=VIGILOS First Boot Setup
After=network-online.target
Wants=network-online.target
ConditionPathExists=!/var/lib/vigilos-first-boot-done

[Service]
Type=oneshot
ExecStart=/usr/local/bin/vigilos-first-boot.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
SERVICEUNIT

systemctl enable vigilos-first-boot.service

# ----------------------
# KDE Plasma Defaults
# ----------------------
mkdir -p /etc/skel/.config

# Default wallpaper (canonical KDE package path)
cat > /etc/skel/.config/plasma-org.kde.plasma.desktop-appletsrc << 'EOF'
[Containments][1][Wallpaper][org.kde.image][General]
Image=/usr/share/wallpapers/VIGILOS/contents/images/1672x941.png
PreviewImage=/usr/share/wallpapers/VIGILOS/contents/images/1672x941.png
EOF

# ----------------------
# SDDM Theme
# ----------------------
mkdir -p /etc/sddm.conf.d
cat > /etc/sddm.conf.d/vigilos.conf << 'EOF'
[Theme]
Current=vigilos

[General]
DisplayServer=wayland
DefaultSession=plasma.desktop

[X11]
ServerArguments=-nolisten tcp
EOF

# Ensure the live environment picks KDE as the session (livesys uses this)
if [ -f /etc/sysconfig/livesys ]; then
    sed -i 's/^livesys_session=.*/livesys_session=\"kde\"/' /etc/sysconfig/livesys
fi

# ----------------------
# Plymouth Theme
# ----------------------
plymouth-set-default-theme vigilos || true

# ----------------------
# GRUB Configuration
# ----------------------
sed -i 's/GRUB_DISTRIBUTOR=.*/GRUB_DISTRIBUTOR="VIGIL OS"/' /etc/default/grub

# Enable GRUB theme
if ! grep -q "GRUB_THEME" /etc/default/grub; then
    echo 'GRUB_THEME="/boot/grub2/themes/vigilos/theme.txt"' >> /etc/default/grub
fi

# Regenerate GRUB config if grub2-mkconfig exists
if [ -x /usr/sbin/grub2-mkconfig ]; then
    grub2-mkconfig -o /boot/grub2/grub.cfg 2>/dev/null || true
fi

# ----------------------
# Fastfetch Configuration
# ----------------------
mkdir -p /etc/skel/.config/fastfetch
cat > /etc/skel/.config/fastfetch/config.jsonc << 'EOF'
{
    "$schema": "https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json",
    "logo": {
        "source": "/usr/share/vigilos/logos/fastfetch-logo.txt",
        "type": "file"
    },
    "display": {
        "separator": " → "
    },
    "modules": [
        "title",
        "separator",
        "os",
        "kernel",
        "uptime",
        "packages",
        "shell",
        "de",
        "wm",
        "terminal",
        "cpu",
        "gpu",
        "memory",
        "disk",
        "break",
        "colors"
    ]
}
EOF

# ----------------------
# Enable Services
# ----------------------
systemctl enable sddm
systemctl enable NetworkManager
systemctl enable bluetooth
systemctl set-default graphical.target

%end

# ============================================
# COPY BRANDING FILES (from build host)
# ============================================
%post --nochroot --log=/mnt/sysimage/root/vigilos-branding.log

BRANDING_SRC="/home/bheffernan/vigilos-build/branding"

# Copy Plymouth theme
if [ -d "$BRANDING_SRC/plymouth/vigilos" ]; then
    cp -r "$BRANDING_SRC/plymouth/vigilos" $INSTALL_ROOT/usr/share/plymouth/themes/
fi

# Copy GRUB theme
if [ -d "$BRANDING_SRC/grub/vigilos" ]; then
    mkdir -p $INSTALL_ROOT/boot/grub2/themes
    cp -r "$BRANDING_SRC/grub/vigilos" $INSTALL_ROOT/boot/grub2/themes/
fi

# Copy SDDM theme
if [ -d "$BRANDING_SRC/sddm/vigilos" ]; then
    mkdir -p $INSTALL_ROOT/usr/share/sddm/themes
    cp -r "$BRANDING_SRC/sddm/vigilos" $INSTALL_ROOT/usr/share/sddm/themes/
fi

# Copy Wallpapers (canonical KDE package dir is VIGILOS; keep lowercase symlink)
if [ -d "$BRANDING_SRC/wallpapers/VIGILOS" ]; then
    mkdir -p $INSTALL_ROOT/usr/share/wallpapers/VIGILOS
    cp -r "$BRANDING_SRC/wallpapers/VIGILOS"/* $INSTALL_ROOT/usr/share/wallpapers/VIGILOS/
    cp "$BRANDING_SRC/wallpapers/default.png" $INSTALL_ROOT/usr/share/wallpapers/VIGILOS.png 2>/dev/null || true
    ln -sf VIGILOS $INSTALL_ROOT/usr/share/wallpapers/vigilos 2>/dev/null || true
fi

# Copy Logos
if [ -d "$BRANDING_SRC/logos" ]; then
    mkdir -p $INSTALL_ROOT/usr/share/vigilos/logos
    mkdir -p $INSTALL_ROOT/usr/share/pixmaps
    cp -r "$BRANDING_SRC/logos"/* $INSTALL_ROOT/usr/share/vigilos/logos/
    cp "$BRANDING_SRC/logos/vigilos-logo.png" $INSTALL_ROOT/usr/share/pixmaps/ 2>/dev/null || true
fi

# Copy Icons (hicolor theme structure)
if [ -d "$BRANDING_SRC/icons" ]; then
    mkdir -p $INSTALL_ROOT/usr/share/icons/hicolor
    # Copy icon directories (16x16, 22x22, etc.) but not index.theme to hicolor
    for dir in "$BRANDING_SRC/icons"/*/; do
        [ -d "$dir" ] && cp -r "$dir" $INSTALL_ROOT/usr/share/icons/hicolor/
    done
fi

# Copy Fastfetch ASCII logo
if [ -f "$BRANDING_SRC/fastfetch/fastfetch-logo.txt" ]; then
    mkdir -p $INSTALL_ROOT/usr/share/vigilos/logos
    cp "$BRANDING_SRC/fastfetch/fastfetch-logo.txt" $INSTALL_ROOT/usr/share/vigilos/logos/
fi

%end
