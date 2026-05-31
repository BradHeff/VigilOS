# ============================================
# ArxisOS KDE Plasma - Fedora 43 Base
# ============================================

# Language and Locale
lang en_AU.UTF-8
keyboard us
timezone Australia/Adelaide --utc

# Security
selinux --enforcing
firewall --enabled --service=mdns,kdeconnect

# Network
network --bootproto=dhcp --device=link --activate --hostname=arxisos

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

# Live user (password: arxisos)
rootpw --iscrypted $6$i0FAwpd5FURzJogK$Q/OYpX8Um3PDAT7Lk6k0sVg7NbpWf0pyG0G5EW5R1qhpMkGPwGqKe2ZLBnXzT3qOUrbF/PvO0Go.TBEu.C6JN/
user --name=arxis --groups=wheel --iscrypted --password=$6$i0FAwpd5FURzJogK$Q/OYpX8Um3PDAT7Lk6k0sVg7NbpWf0pyG0G5EW5R1qhpMkGPwGqKe2ZLBnXzT3qOUrbF/PvO0Go.TBEu.C6JN/

# Repositories
url --mirrorlist=https://mirrors.fedoraproject.org/mirrorlist?repo=fedora-43&arch=x86_64
repo --name=updates --mirrorlist=https://mirrors.fedoraproject.org/mirrorlist?repo=updates-released-f43&arch=x86_64

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
plasma-workspace-x11
plasma-workspace-wayland
kwin-x11
plasma-systemmonitor
plasma-discover
xdg-desktop-portal-kde
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

# Native Applications
firefox
remmina
remmina-plugins-rdp
remmina-plugins-vnc
libreoffice

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
%post --log=/root/arxisos-post.log

# ----------------------
# OS Release Branding
# ----------------------
# Write canonical /usr/lib/os-release (fedora-release ships it there) so no tool
# reports "Fedora"; /etc/os-release becomes a symlink to it.
cat > /usr/lib/os-release << 'EOF'
NAME="ArxisOS"
VERSION="1.2 (Loopback)"
ID=arxisos
ID_LIKE=fedora
VERSION_ID=1.2
VERSION_CODENAME=loopback
PRETTY_NAME="ArxisOS 1.2 (Loopback)"
ANSI_COLOR="0;38;2;129;212;250"
LOGO=arxisos-logo
CPE_NAME="cpe:/o:arxisos:arxisos:1.2"
VARIANT="KDE Plasma"
VARIANT_ID=kde
HOME_URL="https://arxisos.com"
DOCUMENTATION_URL="https://docs.arxisos.com"
SUPPORT_URL="https://support.arxisos.com"
BUG_REPORT_URL="https://github.com/arxisos/arxisos/issues"
PRIVACY_POLICY_URL="https://arxisos.com/privacy"
EOF
ln -sf ../usr/lib/os-release /etc/os-release

cat > /etc/system-release << 'EOF'
ArxisOS release 1.2 (Loopback)
EOF

cat > /etc/arxisos-release << 'EOF'
ArxisOS release 1.2 (Loopback)
EOF

# Console login banners (otherwise inherited from fedora-release / setup).
printf 'ArxisOS 1.2 (Loopback) \\r (\\l)\n\n' > /etc/issue
printf 'ArxisOS 1.2 (Loopback)\n' > /etc/issue.net

# ----------------------
# Anaconda installer profile (bootloader-install fix)
# ----------------------
# Rebranding ID=arxisos stops Anaconda from matching a stock profile in
# /etc/anaconda/profile.d/, so it falls back to efi_dir="default" and the
# bootloader step's gen_grub_cfgstub fails (it writes to /boot/efi/EFI/default,
# but shim/grub2-efi install to EFI/fedora). Ship an arxisos profile that
# inherits the fedora profile -> efi_dir=fedora and GRUB installs cleanly.
mkdir -p /etc/anaconda/profile.d
cat > /etc/anaconda/profile.d/arxisos.conf << 'EOF'
[Profile]
profile_id = arxisos
base_profile = fedora

[Profile Detection]
os_id = arxisos
EOF

# ----------------------
# Flatpak Setup - Repo only (installs at first boot)
# ----------------------
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

# ----------------------
# First Boot Flatpak Installer
# ----------------------
cat > /usr/local/bin/arxisos-first-boot.sh << 'FIRSTBOOT'
#!/bin/bash
MARKER="/var/lib/arxisos-first-boot-done"
[ -f "$MARKER" ] && exit 0

# Wait for network
sleep 15

# Install RPM Fusion repositories
dnf install -y \
    https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-43.noarch.rpm \
    https://download1.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-43.noarch.rpm

# Install multimedia codecs
dnf install -y ffmpeg gstreamer1-plugins-bad-freeworld gstreamer1-plugins-ugly

# Install the proprietary NVIDIA driver if an NVIDIA GPU is present.
# Required for RTX 40xx (Ada Lovelace) and other recent cards that nouveau
# cannot drive. akmod-nvidia blacklists nouveau itself; we keep the kernel
# cmdline blacklist as the pre-driver safety net so first boot reaches a desktop.
if lspci -d 10de: 2>/dev/null | grep -qi 'VGA\|3D'; then
    dnf install -y akmod-nvidia xorg-x11-drv-nvidia-cuda
    # Build the kmod now so the desktop comes up driven on the next boot.
    akmods --force 2>/dev/null || true
fi

# Install flatpak applications
flatpak install -y flathub com.google.Chrome
flatpak install -y flathub io.github.astralvixen.geforce-infinity
flatpak install -y flathub it.mijorus.gearlever
flatpak install -y flathub com.spotify.Client
flatpak install -y flathub com.github.IsmaelMartinez.teams_for_linux
flatpak install -y flathub com.visualstudio.code

touch "$MARKER"
FIRSTBOOT

chmod +x /usr/local/bin/arxisos-first-boot.sh

cat > /etc/systemd/system/arxisos-first-boot.service << 'SERVICEUNIT'
[Unit]
Description=ArxisOS First Boot Setup
After=network-online.target
Wants=network-online.target
ConditionPathExists=!/var/lib/arxisos-first-boot-done

[Service]
Type=oneshot
ExecStart=/usr/local/bin/arxisos-first-boot.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
SERVICEUNIT

systemctl enable arxisos-first-boot.service

# ----------------------
# KDE Plasma Defaults
# ----------------------
mkdir -p /etc/skel/.config

# Default wallpaper (canonical KDE package path)
cat > /etc/skel/.config/plasma-org.kde.plasma.desktop-appletsrc << 'EOF'
[Containments][1][Wallpaper][org.kde.image][General]
Image=/usr/share/wallpapers/ArxisOS/contents/images/3840x2160.png
PreviewImage=/usr/share/wallpapers/ArxisOS/contents/images/3840x2160.png
EOF

# ----------------------
# SDDM Theme
# ----------------------
mkdir -p /etc/sddm.conf.d
cat > /etc/sddm.conf.d/arxisos.conf << 'EOF'
[Theme]
Current=arxisos

[General]
DefaultSession=plasmax11.desktop

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
plymouth-set-default-theme arxisos || true

# ----------------------
# GRUB Configuration
# ----------------------
sed -i 's/GRUB_DISTRIBUTOR=.*/GRUB_DISTRIBUTOR="ArxisOS"/' /etc/default/grub

# Enable GRUB theme
if ! grep -q "GRUB_THEME" /etc/default/grub; then
    echo 'GRUB_THEME="/boot/grub2/themes/arxisos/theme.txt"' >> /etc/default/grub
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
        "source": "/usr/share/arxisos/logos/fastfetch-logo.txt",
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
%post --nochroot --log=/mnt/sysimage/root/arxisos-branding.log

BRANDING_SRC="/home/bheffernan/arxisos-build/branding"

# Copy Plymouth theme
if [ -d "$BRANDING_SRC/plymouth/arxisos" ]; then
    cp -r "$BRANDING_SRC/plymouth/arxisos" $INSTALL_ROOT/usr/share/plymouth/themes/
fi

# Copy GRUB theme
if [ -d "$BRANDING_SRC/grub/arxisos" ]; then
    mkdir -p $INSTALL_ROOT/boot/grub2/themes
    cp -r "$BRANDING_SRC/grub/arxisos" $INSTALL_ROOT/boot/grub2/themes/
fi

# Copy SDDM theme
if [ -d "$BRANDING_SRC/sddm/arxisos" ]; then
    mkdir -p $INSTALL_ROOT/usr/share/sddm/themes
    cp -r "$BRANDING_SRC/sddm/arxisos" $INSTALL_ROOT/usr/share/sddm/themes/
fi

# Copy Wallpapers (canonical KDE package dir is ArxisOS; keep lowercase symlink)
if [ -d "$BRANDING_SRC/wallpapers/ArxisOS" ]; then
    mkdir -p $INSTALL_ROOT/usr/share/wallpapers/ArxisOS
    cp -r "$BRANDING_SRC/wallpapers/ArxisOS"/* $INSTALL_ROOT/usr/share/wallpapers/ArxisOS/
    cp "$BRANDING_SRC/wallpapers/default.png" $INSTALL_ROOT/usr/share/wallpapers/ArxisOS.png 2>/dev/null || true
    ln -sf ArxisOS $INSTALL_ROOT/usr/share/wallpapers/arxisos 2>/dev/null || true
fi

# Copy Logos
if [ -d "$BRANDING_SRC/logos" ]; then
    mkdir -p $INSTALL_ROOT/usr/share/arxisos/logos
    mkdir -p $INSTALL_ROOT/usr/share/pixmaps
    cp -r "$BRANDING_SRC/logos"/* $INSTALL_ROOT/usr/share/arxisos/logos/
    cp "$BRANDING_SRC/logos/arxisos-logo.png" $INSTALL_ROOT/usr/share/pixmaps/ 2>/dev/null || true
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
    mkdir -p $INSTALL_ROOT/usr/share/arxisos/logos
    cp "$BRANDING_SRC/fastfetch/fastfetch-logo.txt" $INSTALL_ROOT/usr/share/arxisos/logos/
fi

%end
