#!/bin/bash
set -euo pipefail

# VIGIL OS fresh official Fedora live-image preparation
# Applies: SDDM, Plasma, Plymouth, GRUB, icons, cursors, wallpapers, logos, skel
# Replaces GNOME with KDE Plasma, GDM with SDDM
# Creates live user with autologin, removes on install

BUILD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$BUILD_DIR/scripts/lib/require-builder.sh"
vigilos_require_builder
BRANDING_DIR="$BUILD_DIR/branding"
PLASMA_CFG_DIR="$BUILD_DIR/PLASMA-CONFIGS"
SKEL_DIR="$BUILD_DIR/Skel"
WORK_DIR="$(mktemp -d "${VIGIL_WORK_ROOT:-/var/tmp}/vigilos-branding.XXXXXX")"
DESKTOP="${VIGIL_DESKTOP:-kde}"
[[ "$DESKTOP" == kde || "$DESKTOP" == i3 ]] || exit 2
ISO_LABEL_DEFAULT="VIGILOS-1-2-${DESKTOP}-x86_64"

input_iso="${1:-}"
output_iso="${2:-$BUILD_DIR/VIGILOS-1.2-x86_64.iso}"
# Absolutize paths now: the script cd's into $WORK_DIR later, so a relative
# output name would otherwise drop the ISO inside the work directory.
input_iso="$(readlink -f "$input_iso")"
output_iso="$(readlink -m "$output_iso")"
[[ ! -e "$output_iso" ]] || { echo "ERROR: Refusing to overwrite $output_iso" >&2; exit 1; }
mkdir -p "$(dirname "$output_iso")"
# Derive an ISO label that matches the output filename unless overridden
ISO_LABEL="${ISO_LABEL:-$ISO_LABEL_DEFAULT}"
[[ -z "$ISO_LABEL" ]] && ISO_LABEL="$ISO_LABEL_DEFAULT"

if [[ -z "$input_iso" || ( ! -f "$input_iso" && ! -b "$input_iso" ) ]]; then
    echo "Usage: $0 <input-iso> [output-iso]"
    exit 1
fi

# Cleanup function - handles ALL exit scenarios including Ctrl+C
cleanup_mounts() {
    local exit_code=$?

    if [ $exit_code -ne 0 ]; then
        echo ""
        echo "ERROR: Script failed (exit code: $exit_code). Cleaning up mounts..."
    fi

    # Unmount bind mounts first (in reverse order) - critical to prevent /dev/null errors
    for mount_point in run sys proc dev; do
        sudo umount -l "$WORK_DIR/squashfs/rootfs/$mount_point" 2>/dev/null || true
        sudo umount -l "$WORK_DIR/squashfs/$mount_point" 2>/dev/null || true
    done

    sleep 1

    # Unmount EFI image if mounted
    sudo umount -l "$WORK_DIR/efi" 2>/dev/null || true
    sudo umount -l "$WORK_DIR/erofs" 2>/dev/null || true

    # Unmount rootfs.img if mounted
    sudo umount -l "$WORK_DIR/squashfs/rootfs" 2>/dev/null || true

    # Unmount squashfs
    sudo umount -l "$WORK_DIR/squashfs" 2>/dev/null || true

    # Unmount ISO
    sudo umount -l "$WORK_DIR/iso" 2>/dev/null || true

    # Detach loop devices
    for loop in $(losetup -a 2>/dev/null | grep "$WORK_DIR" | cut -d: -f1); do
        sudo losetup -d "$loop" 2>/dev/null || true
    done

    if [ $exit_code -ne 0 ]; then
        echo "Cleanup complete."
        exit $exit_code
    fi
}
trap cleanup_mounts EXIT
trap 'exit 1' INT TERM

echo "=== VIGIL OS fresh image preparation ==="
echo "Input : $input_iso"
echo "Output: $output_iso"
echo ""

# Each run owns a fresh work directory; preserve previous runs and their evidence.
mkdir -p "$WORK_DIR"/{iso,squashfs,new_iso,efi}
touch "$WORK_DIR/.vigilos-owned"

# Render into this run's private branding copy; preserve source raster baselines.
SOURCE_BRANDING_DIR="$BRANDING_DIR"
BRANDING_DIR="$WORK_DIR/branding"
rsync -a "$SOURCE_BRANDING_DIR/" "$BRANDING_DIR/"
"$BUILD_DIR/scripts/lib/prepare-brand-assets.sh" "$BRANDING_DIR"

# Helper function
copy_if_exists() {
    local src="$1" dest="$2"
    [[ -e "$src" ]] || return 0
    sudo mkdir -p "$(dirname "$dest")"
    sudo cp -r "$src" "$dest"
}

# Match the installed Fedora 44 spinner watermark bounds, preserving aspect.
make_plymouth_watermark() {
    local src="$BRANDING_DIR/logos/vigilos-watermark.png"
    local dest="$WORK_DIR/vigilos-plymouth-watermark.png"
    [[ -f "$src" ]] || src="$BRANDING_DIR/logos/vigilos-logo.png"
    [[ -f "$src" ]] || { echo 'ERROR: No VIGIL watermark source.' >&2; return 1; }
    if command -v magick >/dev/null; then
        magick "$src" -resize 149x43 -background none -gravity center -extent 149x43 "PNG32:$dest"
    elif command -v convert >/dev/null; then
        convert "$src" -resize 149x43 -background none -gravity center -extent 149x43 "PNG32:$dest"
    else
        echo 'ERROR: ImageMagick is required to preserve boot logo bounds.' >&2
        return 1
    fi
    printf '%s\n' "$dest"
}

echo "Mounting ISO..."
sudo mount -o ro "$input_iso" "$WORK_DIR/iso"

echo "Copying ISO contents (excluding squashfs)..."
sudo rsync -a --exclude='LiveOS/squashfs.img' "$WORK_DIR/iso/" "$WORK_DIR/new_iso/"

echo "Extracting live root filesystem..."
ROOT_IMAGE_FORMAT="$(file -b "$WORK_DIR/iso/LiveOS/squashfs.img")"
if [[ "$ROOT_IMAGE_FORMAT" == *EROFS* ]]; then
    sudo mkdir -p "$WORK_DIR/erofs"
    sudo mount -o loop,ro "$WORK_DIR/iso/LiveOS/squashfs.img" "$WORK_DIR/erofs"
    sudo rsync -aAX "$WORK_DIR/erofs/" "$WORK_DIR/squashfs/"
    sudo umount "$WORK_DIR/erofs"
else
    sudo unsquashfs -d "$WORK_DIR/squashfs" "$WORK_DIR/iso/LiveOS/squashfs.img" > /dev/null
fi

# Detect format and set ROOTFS_DIR
ROOTFS_IMG=$(sudo find "$WORK_DIR/squashfs" -maxdepth 2 -name "rootfs.img" 2>/dev/null | head -1)
MOUNTED_ROOTFS=false
if [[ -n "$ROOTFS_IMG" ]]; then
    echo "Traditional format detected (rootfs.img)"
    ROOTFS_DIR="$WORK_DIR/squashfs/rootfs"
    sudo mkdir -p "$ROOTFS_DIR"
    sudo mount -o loop "$ROOTFS_IMG" "$ROOTFS_DIR"
    MOUNTED_ROOTFS=true
else
    echo "OSBuild format detected (squashfs is rootfs)"
    ROOTFS_DIR="$WORK_DIR/squashfs"
fi

# Bind mounts for chroot operations
echo "Setting up chroot environment..."
sudo mount --bind /dev "$ROOTFS_DIR/dev"
sudo mount --bind /proc "$ROOTFS_DIR/proc"
sudo mount --bind /sys "$ROOTFS_DIR/sys"
sudo mount --bind /run "$ROOTFS_DIR/run"

# Preserve the original resolver configuration; builder DNS is temporary.
if [[ -e "$ROOTFS_DIR/etc/resolv.conf" || -L "$ROOTFS_DIR/etc/resolv.conf" ]]; then
    sudo cp -a "$ROOTFS_DIR/etc/resolv.conf" "$WORK_DIR/resolv.conf.original"
fi
# Ensure DNS works in chroot
if [[ -L "$ROOTFS_DIR/etc/resolv.conf" ]]; then
    sudo rm -f "$ROOTFS_DIR/etc/resolv.conf"
fi
sudo cp -L /etc/resolv.conf "$ROOTFS_DIR/etc/resolv.conf"

# ============================================
# INSTALL KDE PLASMA / REMOVE GNOME
# ============================================
echo ""
echo "=== Updating Fedora base from signed official repositories ==="
sudo chroot "$ROOTFS_DIR" dnf upgrade -y --releasever=44 --refresh

echo "=== Installing KDE Plasma Desktop ==="
echo "  (This may take 10-20 minutes...)"

if [[ "$DESKTOP" == kde ]]; then
sudo chroot "$ROOTFS_DIR" dnf install -y --releasever=44 --allowerasing \
    plasma-desktop plasma-workspace plasma-workspace-wayland sddm sddm-kcm sddm-wayland-plasma \
    konsole dolphin kate ark gwenview okular spectacle \
    plasma-nm plasma-pa bluedevil powerdevil kscreen \
    kwin breeze-gtk breeze-icon-theme \
    xorg-x11-server-Xorg xorg-x11-drv-libinput xorg-x11-xinit \
    plasma-systemmonitor plasma-discover \
    NetworkManager-wifi NetworkManager-bluetooth \
    dbus-x11 xdg-desktop-portal xdg-desktop-portal-kde \
    anaconda-live anaconda-webui webkit2gtk4.1 \
    grub2-efi-x64 grub2-efi-x64-modules shim-x64 \
    grub2-tools grub2-tools-extra efibootmgr grub2-common \
    plymouth plymouth-system-theme plymouth-plugin-script plymouth-plugin-two-step \
    dracut dracut-live dracut-config-generic \
    polkit polkit-kde upower udisks2 rtkit \
    avahi avahi-tools switcheroo-control ModemManager \
    dbus-broker systemd-oomd-defaults \
    selinux-policy-targeted policycoreutils policycoreutils-python-utils \
    remmina remmina-plugins-rdp remmina-plugins-vnc remmina-plugins-spice \
    libreoffice nodejs24 nodejs24-bin nodejs24-npm nodejs24-npm-bin python3 flatpak fastfetch htop git vim-enhanced wget2 curl rsync \
    || { echo "ERROR: Required desktop/installer packages failed to install" >&2; exit 1; }

else
    sudo chroot "$ROOTFS_DIR" dnf -y --releasever=44 install anaconda-live anaconda-webui grub2-efi-x64 grub2-efi-x64-modules shim-x64 grub2-tools grub2-tools-extra efibootmgr grub2-common plymouth plymouth-plugin-script plymouth-plugin-two-step dracut dracut-live dracut-config-generic selinux-policy-targeted policycoreutils policycoreutils-python-utils rsync git fastfetch
fi

# User-selected flagship browser, signed vendor RPM repository and runtime tools.
sudo env VIGIL_BUILD_GUEST=1 bash "$BUILD_DIR/scripts/lib/install-default-apps.sh" "$ROOTFS_DIR"

echo "Removing GNOME packages..."
sudo chroot "$ROOTFS_DIR" dnf remove -y --releasever=44 --noautoremove \
    gnome-shell gnome-session gnome-tour gnome-initial-setup \
    gdm gnome-control-center gnome-settings-daemon \
    2>/dev/null || true

# ============================================
# CONFIGURE DISPLAY MANAGER (SDDM)
# ============================================
echo ""
echo "=== Configuring SDDM and Plasma Session ==="

sudo chroot "$ROOTFS_DIR" systemctl set-default graphical.target 2>/dev/null || true
sudo chroot "$ROOTFS_DIR" systemctl disable gdm.service plasmalogin.service 2>/dev/null || true
sudo chroot "$ROOTFS_DIR" systemctl enable sddm.service 2>/dev/null || true
sudo rm -f "$ROOTFS_DIR/etc/systemd/system/display-manager.service"
sudo ln -sf /usr/lib/systemd/system/sddm.service "$ROOTFS_DIR/etc/systemd/system/display-manager.service"

# ============================================
# CREATE LIVE USER
# ============================================
echo ""
echo "=== Creating Live User ==="

if ! sudo chroot "$ROOTFS_DIR" id liveuser &>/dev/null; then
    sudo chroot "$ROOTFS_DIR" useradd -m -G wheel -s /bin/bash liveuser 2>/dev/null || true
fi
# The live account may already exist in Fedora media; unlock it during the build.
sudo chroot "$ROOTFS_DIR" passwd -d liveuser

sudo mkdir -p "$ROOTFS_DIR/home/liveuser/.config"
sudo mkdir -p "$ROOTFS_DIR/home/liveuser/Desktop"

# Passwordless sudo for live user
echo "liveuser ALL=(ALL) NOPASSWD: ALL" | sudo tee "$ROOTFS_DIR/etc/sudoers.d/liveuser" > /dev/null
sudo chmod 440 "$ROOTFS_DIR/etc/sudoers.d/liveuser"

# Shared live-environment predicate (run only inside the image).
sudo mkdir -p "$ROOTFS_DIR/usr/local/libexec"
sudo tee "$ROOTFS_DIR/usr/local/libexec/vigilos-is-live" >/dev/null << 'IS_LIVE_EOF'
#!/usr/bin/bash
live=false
if [ -d /run/initramfs/live ] || grep -Eq '(^|[[:space:]])(rd[.]live[.]image([=[:space:]]|$)|root=live:)' /proc/cmdline; then
    live=true
fi
if [ "${1:-}" = --installed ]; then
    [ "$live" = false ]
else
    [ "$live" = true ]
fi
IS_LIVE_EOF
sudo chmod 0755 "$ROOTFS_DIR/usr/local/libexec/vigilos-is-live"

# ============================================
# LIVE SESSION AUTOLOGIN SERVICE
# ============================================
echo "  - Creating live session autologin service..."
sudo tee "$ROOTFS_DIR/etc/systemd/system/sddm-live-autologin.service" > /dev/null << 'LIVE_AUTOLOGIN_EOF'
[Unit]
Description=Enable SDDM autologin for live session only
Before=sddm.service display-manager.service
After=local-fs.target

[Service]
Type=oneshot
ExecCondition=/usr/local/libexec/vigilos-is-live
ExecStart=/bin/bash -c '\
    if [ -d /run/initramfs/live ] || grep -q "root=live:" /proc/cmdline 2>/dev/null; then \
        mkdir -p /etc/sddm.conf.d; \
        echo "[Autologin]" > /etc/sddm.conf.d/live-autologin.conf; \
        echo "User=liveuser" >> /etc/sddm.conf.d/live-autologin.conf; \
        echo "Session=plasma" >> /etc/sddm.conf.d/live-autologin.conf; \
        echo "Relogin=false" >> /etc/sddm.conf.d/live-autologin.conf; \
    fi'
ExecStop=/bin/rm -f /etc/sddm.conf.d/live-autologin.conf /etc/lightdm/lightdm.conf.d/99-vigilos-live.conf
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
LIVE_AUTOLOGIN_EOF

sudo chroot "$ROOTFS_DIR" systemctl enable sddm-live-autologin.service 2>/dev/null || true

# ============================================
# LIVEUSER SETUP SERVICE (ensures configs on boot)
# ============================================
echo "  - Creating liveuser setup service..."
sudo tee "$ROOTFS_DIR/etc/systemd/system/liveuser-setup.service" > /dev/null << 'LIVEUSER_SERVICE'
[Unit]
Description=Setup Live User with Plasma configuration
Before=display-manager.service sddm.service
After=systemd-user-sessions.service local-fs.target livesys-late.service

[Service]
Type=oneshot
ExecCondition=/usr/local/libexec/vigilos-is-live
ExecStart=/usr/local/libexec/vigilos-liveuser-setup
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
LIVEUSER_SERVICE

sudo tee "$ROOTFS_DIR/usr/local/libexec/vigilos-liveuser-setup" >/dev/null <<'LIVEUSER_SETUP'
#!/usr/bin/bash
set -euo pipefail
if ! id liveuser >/dev/null 2>&1; then useradd -m -G wheel -s /bin/bash liveuser; fi
passwd -d liveuser
mkdir -p /home/liveuser/Desktop /home/liveuser/.config
rsync -a --ignore-existing /etc/skel/ /home/liveuser/
# Fedora's live setup creates its shortcut and welcome config before this unit.
# Use the product entry rather than showing a second Fedora installer icon.
rm -f /home/liveuser/Desktop/liveinst.desktop
printf '[General]\nLiveEnvironment=false\nLiveInstaller=vigilos-installer\n' > /home/liveuser/.config/plasma-welcomerc
chown -R liveuser:liveuser /home/liveuser
LIVEUSER_SETUP
sudo chmod 0755 "$ROOTFS_DIR/usr/local/libexec/vigilos-liveuser-setup"
bash -n "$ROOTFS_DIR/usr/local/libexec/vigilos-liveuser-setup"

sudo chroot "$ROOTFS_DIR" systemctl enable liveuser-setup.service 2>/dev/null || true

# ============================================
# FIRST-BOOT SERVICE (removes liveuser after install)
# ============================================
echo "  - Creating first-boot cleanup service..."
sudo tee "$ROOTFS_DIR/etc/systemd/system/vigilos-first-boot.service" > /dev/null << 'FIRSTBOOT_EOF'
[Unit]
Description=VIGILOS First Boot Setup - Remove live user and configure Plasma
After=local-fs.target network.target systemd-user-sessions.service
Before=plasma-setup.service display-manager.service
ConditionPathExists=!/var/lib/vigilos-first-boot-done

[Service]
Type=oneshot
ExecCondition=/usr/local/libexec/vigilos-is-live --installed
ExecStart=/usr/bin/bash /usr/local/bin/vigilos-first-boot.sh
ExecStartPost=/bin/touch /var/lib/vigilos-first-boot-done
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
FIRSTBOOT_EOF

# Create the first-boot script (easier to debug than inline)
sudo tee "$ROOTFS_DIR/usr/local/bin/vigilos-first-boot.sh" > /dev/null << 'FIRSTBOOT_SCRIPT'
#!/bin/bash
# Installed-system cleanup. Branding and initramfs are prepared during the build
# and installer; avoid an expensive relabel/rebuild on the first desktop boot.
set -euo pipefail
LOG=/var/log/vigilos-first-boot.log
exec >>"$LOG" 2>&1
printf '%s: VIGIL OS installed-system cleanup starting\n' "$(date --iso-8601=seconds)"
/usr/local/libexec/vigilos-is-live --installed || exit 0
if [[ "$(cat /etc/hostname 2>/dev/null)" == localhost-live ]]; then
    hostnamectl set-hostname localhost
fi
if id liveuser >/dev/null 2>&1; then
    loginctl terminate-user liveuser 2>/dev/null || true
    userdel -r liveuser
fi
rm -f /etc/sudoers.d/liveuser /var/lib/AccountsService/users/liveuser
rm -f /etc/sddm.conf.d/live-autologin.conf /etc/lightdm/lightdm.conf.d/99-vigilos-live.conf
for desktop in /etc/skel/Desktop /home/*/Desktop; do
    [[ -d "$desktop" ]] || continue
    rm -f "$desktop/vigilos-installer.desktop" "$desktop/liveinst.desktop"
done
rm -f /usr/share/applications/vigilos-installer.desktop
/usr/local/libexec/vigilos-configure-installed-boot
printf '%s: VIGIL OS installed-system cleanup complete\n' "$(date --iso-8601=seconds)"
FIRSTBOOT_SCRIPT

sudo chmod +x "$ROOTFS_DIR/usr/local/bin/vigilos-first-boot.sh"
sudo chroot "$ROOTFS_DIR" systemctl enable vigilos-first-boot.service 2>/dev/null || true

# Also create symlink manually as backup (in case chroot systemctl fails)
sudo mkdir -p "$ROOTFS_DIR/etc/systemd/system/multi-user.target.wants"
sudo ln -sf /etc/systemd/system/vigilos-first-boot.service "$ROOTFS_DIR/etc/systemd/system/multi-user.target.wants/vigilos-first-boot.service" 2>/dev/null || true

# ============================================
# GPU DRIVER SETUP (multi-vendor, installed system only)
# ============================================
# Goal: boot freely into the live environment on ANY GPU, and on an INSTALLED
# system pull the right accelerated driver automatically.
#
#   * NVIDIA: nouveau cannot drive Ada Lovelace / RTX 40xx (and is shaky on
#     several newer cards) -> live & pre-driver boots use the nouveau blacklist
#     in the kernel cmdline (simpledrm framebuffer). On first boot of an
#     installed system this service installs akmod-nvidia from RPM Fusion and
#     builds the kmod, then notifies the user to reboot into the real driver.
#   * AMD (amdgpu) / Intel (i915): in-kernel KMS already works out of the box,
#     so nothing to install -- the blacklist does not touch them.
#
# This runs in its own network-gated, marker-guarded oneshot service so any
# failure (no network, repo down) is isolated and never blocks the desktop.
echo "  - Creating GPU driver setup service..."

sudo tee "$ROOTFS_DIR/usr/local/bin/vigilos-gpu-setup.sh" > /dev/null << 'GPUSETUP_SCRIPT'
#!/bin/bash
# VIGILOS GPU setup - optional, installed-system-only, retries after failure.
set -euo pipefail
LOG="/var/log/vigilos-gpu-setup.log"
echo "$(date): VIGILOS GPU setup starting" >> "$LOG"

# Never run in the live environment.
if [ -d /run/initramfs/live ] || grep -q "rd.live" /proc/cmdline 2>/dev/null; then
    echo "$(date): live environment - skipping GPU setup" >> "$LOG"
    exit 0
fi

# Detect an NVIDIA display controller without depending on pciutils:
# PCI vendor 0x10de + class VGA (0x0300xx) or 3D controller (0x0302xx).
nvidia_present() {
    local v cls dev
    for v in /sys/bus/pci/devices/*/vendor; do
        [ -r "$v" ] || continue
        [ "$(cat "$v" 2>/dev/null)" = "0x10de" ] || continue
        dev="$(dirname "$v")"
        cls="$(cat "$dev/class" 2>/dev/null)"
        case "$cls" in
            0x0300*|0x0302*) return 0 ;;
        esac
    done
    return 1
}

if ! nvidia_present; then
    echo "$(date): no NVIDIA GPU detected (AMD/Intel use in-kernel KMS, nothing to do)" >> "$LOG"
    exit 0
fi

echo "$(date): NVIDIA GPU detected - installing proprietary driver" >> "$LOG"

# RPM Fusion (free + nonfree) provides akmod-nvidia.
dnf install -y \
    "https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm" \
    "https://download1.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm" \
    >> "$LOG" 2>&1 || { echo "$(date): ERROR repository setup failed; retry next boot" >> "$LOG"; exit 1; }

if dnf install -y akmod-nvidia xorg-x11-drv-nvidia-cuda >> "$LOG" 2>&1; then
    # Build the kmod now so the driver is ready on the next boot.
    akmods --force >> "$LOG" 2>&1 || { echo "$(date): ERROR module build failed; retry next boot" >> "$LOG"; exit 1; }
    modinfo -k "$(uname -r)" nvidia >> "$LOG" 2>&1 || { echo "$(date): ERROR NVIDIA module unavailable; retry next boot" >> "$LOG"; exit 1; }
    # Flag for the per-user notifier (autostart) to prompt a reboot.
    touch /var/lib/vigilos-nvidia-ready
    echo "$(date): akmod-nvidia installed; reboot flag set" >> "$LOG"
else
    echo "$(date): ERROR driver install failed; retry next boot" >> "$LOG"
    exit 1
fi

echo "$(date): GPU setup complete" >> "$LOG"
GPUSETUP_SCRIPT
sudo chmod +x "$ROOTFS_DIR/usr/local/bin/vigilos-gpu-setup.sh"

sudo tee "$ROOTFS_DIR/etc/systemd/system/vigilos-gpu-setup.service" > /dev/null << 'GPUSETUP_EOF'
[Unit]
Description=VIGILOS GPU Driver Setup (installs NVIDIA driver on first boot)
After=network-online.target
Wants=network-online.target
ConditionPathExists=!/var/lib/vigilos-gpu-setup-done
ConditionKernelCommandLine=!rd.live.image
# Official-only builds defer proprietary driver repository setup.
ConditionPathExists=/etc/vigilos/enable-third-party-gpu

[Service]
Type=oneshot
ExecCondition=/usr/local/libexec/vigilos-is-live --installed
ExecStart=/usr/local/bin/vigilos-gpu-setup.sh
ExecStartPost=/bin/touch /var/lib/vigilos-gpu-setup-done
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
GPUSETUP_EOF
# Keep this opt-in unit disabled so it cannot pull network-online.target into
# the normal boot transaction merely to skip its third-party condition.
sudo chroot "$ROOTFS_DIR" systemctl disable vigilos-gpu-setup.service 2>/dev/null || true
sudo rm -f "$ROOTFS_DIR/etc/systemd/system/multi-user.target.wants/vigilos-gpu-setup.service"

# Per-user notifier: when the NVIDIA driver has been built, prompt to reboot.
sudo tee "$ROOTFS_DIR/usr/local/bin/vigilos-gpu-notify.sh" > /dev/null << 'GPUNOTIFY_SCRIPT'
#!/bin/bash
# Shown via KDE autostart. Prompts the user to reboot once the NVIDIA driver
# has been installed/built, then marks itself shown for this user.
[ -f /var/lib/vigilos-nvidia-ready ] || exit 0
SHOWN="$HOME/.config/vigilos-nvidia-notified"
[ -f "$SHOWN" ] && exit 0

TITLE="VIGIL OS — NVIDIA driver ready"
MSG="The proprietary NVIDIA driver has been installed and built. Please reboot to enable full graphics acceleration."

if command -v kdialog >/dev/null 2>&1; then
    kdialog --title "$TITLE" --passivepopup "$MSG" 20 >/dev/null 2>&1 || \
    kdialog --title "$TITLE" --msgbox "$MSG" >/dev/null 2>&1 || true
elif command -v notify-send >/dev/null 2>&1; then
    notify-send -u critical -t 20000 "$TITLE" "$MSG" >/dev/null 2>&1 || true
fi

mkdir -p "$HOME/.config" && touch "$SHOWN"
GPUNOTIFY_SCRIPT
sudo chmod +x "$ROOTFS_DIR/usr/local/bin/vigilos-gpu-notify.sh"

# Autostart entry seeded into /etc/skel so every user gets the one-time prompt.
sudo mkdir -p "$ROOTFS_DIR/etc/skel/.config/autostart"
sudo tee "$ROOTFS_DIR/etc/skel/.config/autostart/vigilos-gpu-notify.desktop" > /dev/null << 'GPUNOTIFY_DESKTOP'
[Desktop Entry]
Type=Application
Name=VIGILOS NVIDIA Driver Notice
Exec=/usr/local/bin/vigilos-gpu-notify.sh
Icon=vigilos-logo
X-KDE-autostart-after=panel
OnlyShowIn=KDE;
NoDisplay=true
GPUNOTIFY_DESKTOP

# ============================================
# PLYMOUTH THEME
# ============================================
echo ""
echo "=== Applying Plymouth Boot Splash ==="

if [[ -d "$BRANDING_DIR/plymouth/vigilos" ]]; then
    echo "  - Copying VIGILOS Plymouth theme..."
    sudo mkdir -p "$ROOTFS_DIR/usr/share/plymouth/themes/vigilos"
    sudo cp -r "$BRANDING_DIR/plymouth/vigilos/"* "$ROOTFS_DIR/usr/share/plymouth/themes/vigilos/"

    sudo mkdir -p "$ROOTFS_DIR/usr/share/plymouth/themes/vigilos-spinner"
    sudo cp -a "$ROOTFS_DIR/usr/share/plymouth/themes/spinner/." "$ROOTFS_DIR/usr/share/plymouth/themes/vigilos-spinner/"
    sudo cp "$ROOTFS_DIR/usr/share/plymouth/themes/spinner/spinner.plymouth" "$ROOTFS_DIR/usr/share/plymouth/themes/vigilos-spinner/vigilos-spinner.plymouth"
    sudo sed -i -e 's@ImageDir=.*@ImageDir=/usr/share/plymouth/themes/vigilos-spinner@' -e 's/^Name=.*/Name=VIGIL OS/' "$ROOTFS_DIR/usr/share/plymouth/themes/vigilos-spinner/vigilos-spinner.plymouth"

    # Configure Plymouth - use spinner theme with VIGILOS watermark for reliability
    # The vigilos theme uses two-step which may not work on all systems
    sudo mkdir -p "$ROOTFS_DIR/etc/plymouth"
    sudo tee "$ROOTFS_DIR/etc/plymouth/plymouthd.conf" >/dev/null <<'PLYCONF'
[Daemon]
Theme=vigilos-spinner
ShowDelay=0
DeviceTimeout=8
PLYCONF

    # Replace watermarks in spinner and bgrt themes with VIGILOS logo
    # Use pre-generated 128x128 watermark (original is 980x980 which fills entire screen)
    echo "  - Replacing Plymouth watermarks..."
    PLYMOUTH_LOGO=""

    PLYMOUTH_LOGO="$(make_plymouth_watermark)"

    # Only replace if we have a valid watermark
    if [[ -n "$PLYMOUTH_LOGO" && -f "$PLYMOUTH_LOGO" ]]; then
        # Replace in spinner theme (boot)
        if [[ -d "$ROOTFS_DIR/usr/share/plymouth/themes/spinner" ]]; then
            sudo cp "$PLYMOUTH_LOGO" "$ROOTFS_DIR/usr/share/plymouth/themes/spinner/watermark.png"
            echo "    - Replaced spinner watermark"
        fi

        # Replace in bgrt theme
        if [[ -d "$ROOTFS_DIR/usr/share/plymouth/themes/bgrt" ]]; then
            sudo cp "$PLYMOUTH_LOGO" "$ROOTFS_DIR/usr/share/plymouth/themes/bgrt/watermark.png"
            echo "    - Replaced bgrt watermark"
        fi

        # Replace in hot theme (shutdown/reboot - the red/green arrows theme)
        if [[ -d "$ROOTFS_DIR/usr/share/plymouth/themes/hot" ]]; then
            sudo cp "$PLYMOUTH_LOGO" "$ROOTFS_DIR/usr/share/plymouth/themes/hot/watermark.png"
            # Also replace any logo files in hot theme
            for logo_file in "$ROOTFS_DIR/usr/share/plymouth/themes/hot/"*logo*.png; do
                [[ -f "$logo_file" ]] && sudo cp "$PLYMOUTH_LOGO" "$logo_file"
            done
            echo "    - Replaced hot theme watermark (shutdown/reboot)"
        fi

        # Replace in tribar theme (another shutdown theme variant)
        if [[ -d "$ROOTFS_DIR/usr/share/plymouth/themes/tribar" ]]; then
            sudo cp "$PLYMOUTH_LOGO" "$ROOTFS_DIR/usr/share/plymouth/themes/tribar/watermark.png"
            echo "    - Replaced tribar watermark"
        fi

        # Replace in text theme
        if [[ -d "$ROOTFS_DIR/usr/share/plymouth/themes/text" ]]; then
            sudo cp "$PLYMOUTH_LOGO" "$ROOTFS_DIR/usr/share/plymouth/themes/text/watermark.png" 2>/dev/null || true
        fi

        # Also replace the logo.png in vigilos theme
        if [[ -d "$ROOTFS_DIR/usr/share/plymouth/themes/vigilos" ]]; then
            sudo cp "$PLYMOUTH_LOGO" "$ROOTFS_DIR/usr/share/plymouth/themes/vigilos/logo.png"
            echo "    - Replaced vigilos theme logo"
        fi

        # Replace watermark in ALL Plymouth themes to be safe
        echo "    - Replacing watermarks in all Plymouth themes..."
        for theme_dir in "$ROOTFS_DIR/usr/share/plymouth/themes/"*/; do
            [[ -d "$theme_dir" ]] || continue
            theme_name=$(basename "$theme_dir")
            # Replace watermark.png if it exists
            if [[ -f "${theme_dir}watermark.png" ]]; then
                sudo cp "$PLYMOUTH_LOGO" "${theme_dir}watermark.png"
            fi
            # Replace any file with 'logo' in the name
            for logo_file in "${theme_dir}"*logo*.png "${theme_dir}"*Logo*.png; do
                [[ -f "$logo_file" ]] && sudo cp "$PLYMOUTH_LOGO" "$logo_file"
            done
        done
    fi

    # Clean up temp file if we created one
    # Keep generated watermark with this run's build evidence.

    # Configure Plymouth for installed system
    echo "  - Configuring Plymouth for installed system..."

    # Create dracut configuration to include Plymouth
    sudo mkdir -p "$ROOTFS_DIR/etc/dracut.conf.d"
    sudo tee "$ROOTFS_DIR/etc/dracut.conf.d/plymouth.conf" > /dev/null << 'DRACUTCONF'
# Include Plymouth in initramfs for boot splash
add_dracutmodules+=" plymouth "
DRACUTCONF

    # Create dracut module to ensure VIGILOS branding is in initramfs
    echo "  - Creating dracut module for VIGILOS plymouth branding"
    sudo mkdir -p "$ROOTFS_DIR/usr/lib/dracut/modules.d/99vigilos-branding"
    sudo tee "$ROOTFS_DIR/usr/lib/dracut/modules.d/99vigilos-branding/module-setup.sh" > /dev/null << 'DRACUT_MODULE'
#!/bin/bash
# VIGILOS Plymouth branding dracut module

check() {
    return 0
}

depends() {
    echo plymouth
    return 0
}

install() {
    # Install VIGILOS watermark to spinner theme in initramfs
    if [ -f /usr/share/plymouth/themes/spinner/watermark.png ]; then
        inst_simple /usr/share/plymouth/themes/spinner/watermark.png
    fi
    # Install to bgrt theme as well
    if [ -f /usr/share/plymouth/themes/bgrt/watermark.png ]; then
        inst_simple /usr/share/plymouth/themes/bgrt/watermark.png
    fi
    # Install to tribar theme (shutdown/reboot)
    if [ -f /usr/share/plymouth/themes/tribar/watermark.png ]; then
        inst_simple /usr/share/plymouth/themes/tribar/watermark.png
    fi
    # Install VIGILOS theme if available
    if [ -d /usr/share/plymouth/themes/vigilos ]; then
        inst_dir /usr/share/plymouth/themes/vigilos
        for f in /usr/share/plymouth/themes/vigilos/*; do
            [ -f "$f" ] && inst_simple "$f"
        done
    fi
    inst_dir /usr/share/plymouth/themes/vigilos-spinner
    for f in /usr/share/plymouth/themes/vigilos-spinner/*; do
        [ -f "$f" ] && inst_simple "$f"
    done
    # Ensure Plymouth config is in initramfs
    if [ -f /etc/plymouth/plymouthd.conf ]; then
        inst_simple /etc/plymouth/plymouthd.conf
    fi
}
DRACUT_MODULE
    sudo chmod +x "$ROOTFS_DIR/usr/lib/dracut/modules.d/99vigilos-branding/module-setup.sh"

    # Create dracut configuration to always include the branding module
    sudo tee "$ROOTFS_DIR/etc/dracut.conf.d/vigilos-branding.conf" > /dev/null << 'DRACUT_CONF'
# VIGILOS branding - include plymouth watermarks in initramfs
add_dracutmodules+=" vigilos-branding "
# Bound peak memory during installation and later kernel updates.
compress="zstd -3 -q -T1"
DRACUT_CONF

    # Set Plymouth default theme to spinner (with VIGILOS watermark)
    if [[ -f "$ROOTFS_DIR/usr/sbin/plymouth-set-default-theme" ]]; then
        sudo ln -sf /usr/share/plymouth/themes/vigilos-spinner/vigilos-spinner.plymouth "$ROOTFS_DIR/etc/alternatives/default.plymouth" 2>/dev/null || true
        sudo chroot "$ROOTFS_DIR" plymouth-set-default-theme vigilos-spinner 2>/dev/null || true
    fi
fi

# ============================================
# GRUB THEME (inside rootfs for installed system)
# ============================================
echo ""
echo "=== Applying GRUB Theme ==="

if [[ -d "$BRANDING_DIR/grub/vigilos" ]]; then
    echo "  - Copying GRUB theme to rootfs..."
    sudo mkdir -p "$ROOTFS_DIR/boot/grub2/themes/vigilos"
    sudo cp -r "$BRANDING_DIR/grub/vigilos/"* "$ROOTFS_DIR/boot/grub2/themes/vigilos/"

    # Also copy to /usr/share for installed system (first-boot will copy to /boot)
    echo "  - Copying GRUB theme to /usr/share for installed system..."
    sudo mkdir -p "$ROOTFS_DIR/usr/share/grub/themes/vigilos"
    sudo cp -r "$BRANDING_DIR/grub/vigilos/"* "$ROOTFS_DIR/usr/share/grub/themes/vigilos/"

    # Generate GRUB fonts
    echo "  - Generating GRUB fonts..."
    GRUB_MKFONT=""
    if command -v grub2-mkfont &> /dev/null; then
        GRUB_MKFONT="grub2-mkfont"
    elif command -v grub-mkfont &> /dev/null; then
        GRUB_MKFONT="grub-mkfont"
    fi

    if [[ -n "$GRUB_MKFONT" ]]; then
        DEJAVU_REGULAR=$(find /usr/share/fonts -name "DejaVuSans.ttf" 2>/dev/null | head -1)
        DEJAVU_BOLD=$(find /usr/share/fonts -name "DejaVuSans-Bold.ttf" 2>/dev/null | head -1)

        if [[ -n "$DEJAVU_REGULAR" ]]; then
            sudo $GRUB_MKFONT -n dejavu_sans_16 -s 16 -o "$ROOTFS_DIR/boot/grub2/themes/vigilos/dejavu_sans_16.pf2" "$DEJAVU_REGULAR" 2>/dev/null || true
            sudo $GRUB_MKFONT -n dejavu_sans_11 -s 11 -o "$ROOTFS_DIR/boot/grub2/themes/vigilos/dejavu_sans_11.pf2" "$DEJAVU_REGULAR" 2>/dev/null || true
        fi
        if [[ -n "$DEJAVU_BOLD" ]]; then
            sudo $GRUB_MKFONT -n dejavu_sans_bold_16 -s 16 -o "$ROOTFS_DIR/boot/grub2/themes/vigilos/dejavu_sans_bold_16.pf2" "$DEJAVU_BOLD" 2>/dev/null || true
            sudo $GRUB_MKFONT -n dejavu_sans_bold_24 -s 24 -o "$ROOTFS_DIR/boot/grub2/themes/vigilos/dejavu_sans_bold_24.pf2" "$DEJAVU_BOLD" 2>/dev/null || true
        fi
    fi

    # Copy unicode.pf2 fallback
    if [[ -f /usr/share/grub/unicode.pf2 ]]; then
        sudo cp /usr/share/grub/unicode.pf2 "$ROOTFS_DIR/boot/grub2/themes/vigilos/" 2>/dev/null || true
    elif [[ -f /boot/grub2/fonts/unicode.pf2 ]]; then
        sudo cp /boot/grub2/fonts/unicode.pf2 "$ROOTFS_DIR/boot/grub2/themes/vigilos/" 2>/dev/null || true
    fi

    sudo cp "$ROOTFS_DIR/boot/grub2/themes/vigilos/"*.pf2 "$ROOTFS_DIR/usr/share/grub/themes/vigilos/"

    # Configure GRUB defaults
    echo "  - Configuring GRUB defaults..."
    sudo sed -i '/^GRUB_THEME=/d;/^GRUB_DISTRIBUTOR=/d;/^GRUB_DISABLE_OS_PROBER=/d;/^GRUB_GFXMODE=/d;/^GRUB_GFXPAYLOAD_LINUX=/d' "$ROOTFS_DIR/etc/default/grub" 2>/dev/null || true

    # Ensure rhgb quiet is in GRUB_CMDLINE_LINUX for Plymouth splash.
    # Also blacklist nouveau so a disk-installed VIGILOS boots to a desktop on
    # NVIDIA Ada Lovelace / RTX 40xx hardware (nouveau KMS = black screen there).
    # The akmod-nvidia proprietary driver (installed at first boot by
    # vigilos-gpu-setup.service) blacklists nouveau itself once present, so this
    # is the pre-driver safety net that gets us to a desktop on any GPU.
    GRUB_EXTRA_CMDLINE="rhgb quiet rd.driver.blacklist=nouveau modprobe.blacklist=nouveau nouveau.modeset=0"
    if grep -q "^GRUB_CMDLINE_LINUX=" "$ROOTFS_DIR/etc/default/grub" 2>/dev/null; then
        # Add rhgb quiet if not already present
        if ! grep -q "rhgb" "$ROOTFS_DIR/etc/default/grub"; then
            sudo sed -i "s/^GRUB_CMDLINE_LINUX=\"\(.*\)\"/GRUB_CMDLINE_LINUX=\"\1 ${GRUB_EXTRA_CMDLINE}\"/" "$ROOTFS_DIR/etc/default/grub"
        fi
    else
        echo "GRUB_CMDLINE_LINUX=\"${GRUB_EXTRA_CMDLINE}\"" | sudo tee -a "$ROOTFS_DIR/etc/default/grub" >/dev/null
    fi

    sudo mkdir -p "$ROOTFS_DIR/etc/default"
    sudo tee -a "$ROOTFS_DIR/etc/default/grub" >/dev/null <<'GRUBCONF'

# VIGILOS GRUB Configuration
GRUB_THEME="/boot/grub2/themes/vigilos/theme.txt"
GRUB_DISTRIBUTOR="VIGIL OS"
GRUB_DISABLE_OS_PROBER=true
GRUB_GFXMODE=auto
GRUB_GFXPAYLOAD_LINUX=keep
GRUB_TERMINAL_OUTPUT="gfxterm"
GRUBCONF
fi

# ============================================
# GRUB THEME ON ISO BOOT (EFI and BIOS)
# ============================================
echo ""
echo "=== Branding ISO Boot Menu ==="

# Copy GRUB theme to ISO directories
if [[ -d "$BRANDING_DIR/grub/vigilos" ]]; then
    echo "  - Copying GRUB theme to ISO..."
    sudo mkdir -p "$WORK_DIR/new_iso/EFI/BOOT/themes/vigilos"
    sudo cp -r "$BRANDING_DIR/grub/vigilos/"* "$WORK_DIR/new_iso/EFI/BOOT/themes/vigilos/"
    sudo mkdir -p "$WORK_DIR/new_iso/boot/grub2/themes/vigilos"
    sudo cp -r "$BRANDING_DIR/grub/vigilos/"* "$WORK_DIR/new_iso/boot/grub2/themes/vigilos/"

    # Generate fonts for ISO theme directories
    if [[ -n "${GRUB_MKFONT:-}" ]]; then
        for THEME_DIR in "$WORK_DIR/new_iso/EFI/BOOT/themes/vigilos" "$WORK_DIR/new_iso/boot/grub2/themes/vigilos"; do
            sudo cp "$ROOTFS_DIR/boot/grub2/themes/vigilos/"*.pf2 "$THEME_DIR/"
            if [[ -n "${DEJAVU_REGULAR:-}" ]]; then
                sudo $GRUB_MKFONT -n dejavu_sans_16 -s 16 -o "$THEME_DIR/dejavu_sans_16.pf2" "$DEJAVU_REGULAR" 2>/dev/null || true
            fi
            if [[ -n "${DEJAVU_BOLD:-}" ]]; then
                sudo $GRUB_MKFONT -n dejavu_sans_bold_24 -s 24 -o "$THEME_DIR/dejavu_sans_bold_24.pf2" "$DEJAVU_BOLD" 2>/dev/null || true
            fi
            [[ -f /usr/share/grub/unicode.pf2 ]] && sudo cp /usr/share/grub/unicode.pf2 "$THEME_DIR/" 2>/dev/null || true
        done
    fi

    # Vector derivatives are already 8-bit RGBA PNG. Keep transparency so the
    # mark has no opaque black rectangle on the GRUB background.

fi

# Update EFI GRUB config
if [[ -f "$WORK_DIR/new_iso/EFI/BOOT/grub.cfg" ]]; then
    echo "  - Updating EFI GRUB config..."
    sudo sed -i \
        -e "s/CDLABEL=Fedora-[0-9A-Za-z_-]*/CDLABEL=${ISO_LABEL}/g" \
        -e "s/-l 'Fedora-[^']*'/-l '${ISO_LABEL}'/g" \
        -e "s/Install Fedora [0-9]*/Start VIGIL OS/g" \
        -e "s/Test this media & install Fedora [0-9]*/Test Media \& Start VIGIL OS/g" \
        -e "s/Install Fedora [0-9]* in basic graphics mode/Start VIGIL OS (Basic Graphics)/g" \
        -e "s/Rescue a Fedora system/Rescue VIGIL OS System/g" \
        -e "s/--class fedora/--class vigilos/g" \
        "$WORK_DIR/new_iso/EFI/BOOT/grub.cfg"

    # Keep enforcing SELinux for live boot plus splash flags.
    # nouveau.modeset=0 + blacklist: nouveau has no working KMS on NVIDIA Ada
    # Lovelace (RTX 40-series, e.g. 4080 = AD103) and similar new GPUs. Without
    # this the GRUB/Plymouth splash shows (firmware framebuffer) but the desktop
    # is a black screen with only an X cursor once nouveau tries to mode-set.
    # Blacklisting it keeps the generic simpledrm/efifb framebuffer into the
    # desktop. Targeted (not global nomodeset) so Intel/AMD iGPU KMS still works.
    sudo sed -i \
        -e '/^\s*linux/s/$/ selinux=1 enforcing=1 rhgb quiet rd.driver.blacklist=nouveau modprobe.blacklist=nouveau nouveau.modeset=0/' \
        -e '/^\s*linuxefi/s/$/ selinux=1 enforcing=1 rhgb quiet rd.driver.blacklist=nouveau modprobe.blacklist=nouveau nouveau.modeset=0/' \
        "$WORK_DIR/new_iso/EFI/BOOT/grub.cfg"

    # Add theme configuration
    if ! grep -q "set theme=" "$WORK_DIR/new_iso/EFI/BOOT/grub.cfg"; then
        {
            echo '# VIGILOS GRUB Theme'
            echo 'insmod all_video'
            echo 'insmod gfxterm'
            echo 'insmod gfxmenu'
            echo 'insmod png'
            echo 'set gfxmode=auto'
            echo 'terminal_output gfxterm'
            echo 'set theme=($root)/EFI/BOOT/themes/vigilos/theme.txt'
            echo ''
            cat "$WORK_DIR/new_iso/EFI/BOOT/grub.cfg"
        } | sudo tee "$WORK_DIR/new_iso/EFI/BOOT/grub.cfg.new" > /dev/null
        sudo mv "$WORK_DIR/new_iso/EFI/BOOT/grub.cfg.new" "$WORK_DIR/new_iso/EFI/BOOT/grub.cfg"
    fi
fi

# Update BIOS GRUB config
if [[ -f "$WORK_DIR/new_iso/boot/grub2/grub.cfg" ]]; then
    echo "  - Updating BIOS GRUB config..."
    sudo sed -i \
        -e "s/CDLABEL=Fedora-[0-9A-Za-z_-]*/CDLABEL=${ISO_LABEL}/g" \
        -e "s/-l 'Fedora-[^']*'/-l '${ISO_LABEL}'/g" \
        -e "s/Install Fedora [0-9]*/Start VIGIL OS/g" \
        -e "s/Test this media & install Fedora [0-9]*/Test Media \& Start VIGIL OS/g" \
        -e "s/Install Fedora [0-9]* in basic graphics mode/Start VIGIL OS (Basic Graphics)/g" \
        -e "s/Rescue a Fedora system/Rescue VIGIL OS System/g" \
        -e "s/--class fedora/--class vigilos/g" \
        "$WORK_DIR/new_iso/boot/grub2/grub.cfg"

    # Keep enforcing SELinux for live boot plus splash flags.
    # See EFI block above for why nouveau is blacklisted (Ada Lovelace / RTX 40xx
    # black-screen-with-cursor). Keep both blocks in sync.
    sudo sed -i \
        -e '/^\s*linux/s/$/ selinux=1 enforcing=1 rhgb quiet rd.driver.blacklist=nouveau modprobe.blacklist=nouveau nouveau.modeset=0/' \
        -e '/^\s*linuxefi/s/$/ selinux=1 enforcing=1 rhgb quiet rd.driver.blacklist=nouveau modprobe.blacklist=nouveau nouveau.modeset=0/' \
        "$WORK_DIR/new_iso/boot/grub2/grub.cfg"

    if ! grep -q "set theme=" "$WORK_DIR/new_iso/boot/grub2/grub.cfg"; then
        {
            echo '# VIGILOS GRUB Theme'
            echo 'insmod all_video'
            echo 'insmod gfxterm'
            echo 'insmod gfxmenu'
            echo 'insmod png'
            echo 'set gfxmode=auto'
            echo 'terminal_output gfxterm'
            echo 'set theme=($root)/boot/grub2/themes/vigilos/theme.txt'
            echo ''
            cat "$WORK_DIR/new_iso/boot/grub2/grub.cfg"
        } | sudo tee "$WORK_DIR/new_iso/boot/grub2/grub.cfg.new" > /dev/null
        sudo mv "$WORK_DIR/new_iso/boot/grub2/grub.cfg.new" "$WORK_DIR/new_iso/boot/grub2/grub.cfg"
    fi
fi

sudo python3 "$BUILD_DIR/scripts/lib/brand-grub.py" "$WORK_DIR/new_iso"
grub2-script-check "$WORK_DIR/new_iso/boot/grub2/grub.cfg"
grub2-script-check "$WORK_DIR/new_iso/EFI/BOOT/grub.cfg"

# ============================================
# SDDM THEME
# ============================================
echo ""
echo "=== Applying SDDM Theme ==="

SDDM_SRC=""
if [[ -d "$PLASMA_CFG_DIR/VIGILOS-SDDM" ]]; then
    SDDM_SRC="$PLASMA_CFG_DIR/VIGILOS-SDDM"
elif [[ -d "$BRANDING_DIR/sddm/vigilos" ]]; then
    SDDM_SRC="$BRANDING_DIR/sddm/vigilos"
fi

if [[ -n "$SDDM_SRC" ]]; then
    echo "  - Copying SDDM theme..."
    sudo mkdir -p "$ROOTFS_DIR/usr/share/sddm/themes/vigilos"
    sudo cp -r "$SDDM_SRC/"* "$ROOTFS_DIR/usr/share/sddm/themes/vigilos/"

    # Set VIGILOS logo as default face icon
    if [[ -f "$BRANDING_DIR/logos/vigilos-logo.png" ]]; then
        sudo mkdir -p "$ROOTFS_DIR/usr/share/sddm/faces"
        sudo cp "$BRANDING_DIR/logos/vigilos-logo.png" "$ROOTFS_DIR/usr/share/sddm/faces/.face.icon"
        sudo mkdir -p "$ROOTFS_DIR/usr/share/sddm/themes/vigilos/faces"
        sudo cp "$BRANDING_DIR/logos/vigilos-logo.png" "$ROOTFS_DIR/usr/share/sddm/themes/vigilos/faces/.face.icon"
    fi
fi

# SDDM configuration
echo "  - Configuring SDDM..."
sudo mkdir -p "$ROOTFS_DIR/etc/sddm.conf.d"
sudo tee "$ROOTFS_DIR/etc/sddm.conf.d/vigilos.conf" >/dev/null <<'SDDMEOF'
[Theme]
Current=vigilos
CursorTheme=oreo_white_cursors

[General]
DisplayServer=wayland
DefaultSession=plasma.desktop

[X11]
ServerArguments=-nolisten tcp

[Wayland]
SessionDir=/usr/share/wayland-sessions
SDDMEOF

# ============================================
# PLASMA THEMES AND LOOK-AND-FEEL (PurPurDay)
# ============================================
echo ""
echo "=== Applying Plasma Themes (PurPurDay) ==="

echo "  - Wallpapers..."
# Copy VIGILOS wallpaper package (proper Plasma wallpaper structure)
if [[ -d "$BRANDING_DIR/wallpapers/VIGILOS" ]]; then
    sudo mkdir -p "$ROOTFS_DIR/usr/share/vigilos/wallpapers/VIGILOS"
    sudo cp -r "$BRANDING_DIR/wallpapers/VIGILOS/"* "$ROOTFS_DIR/usr/share/vigilos/wallpapers/VIGILOS/"
fi
# Also copy standalone wallpapers for compatibility

# Product wallpaper defaults are provided through a separate look-and-feel package.
# Keep upstream F44 artwork/metadata unchanged; XDG overlays cover compatibility IDs.
echo "  - Logos..."
copy_if_exists "$BRANDING_DIR/logos" "$ROOTFS_DIR/usr/share/vigilos/logos"
copy_if_exists "$BRANDING_DIR/logos/vigilos-logo.png" "$ROOTFS_DIR/usr/share/pixmaps/vigilos-logo.png"
# Copy canonical normalized watermark for Plymouth first-boot regeneration
sudo cp "$BRANDING_DIR/logos/vigilos-watermark.png" "$ROOTFS_DIR/usr/share/pixmaps/vigilos-watermark.png"
# Retain the legacy square icon for compatibility, not for boot splash selection.
if [[ -f "$BRANDING_DIR/logos/vigilos-watermark-128.png" ]]; then
    sudo cp "$BRANDING_DIR/logos/vigilos-watermark-128.png" "$ROOTFS_DIR/usr/share/pixmaps/vigilos-watermark-128.png"
    sudo cp "$BRANDING_DIR/logos/vigilos-watermark-128.png" "$ROOTFS_DIR/usr/share/vigilos/logos/vigilos-watermark-128.png"
    echo "    - Watermark 128x128 copied for Plymouth"
fi

echo "  - Icon themes..."
if [[ -d "$BRANDING_DIR/icons/hicolor" ]]; then
    sudo mkdir -p "$ROOTFS_DIR/usr/share/icons/hicolor"
    sudo cp -r "$BRANDING_DIR/icons/hicolor/"* "$ROOTFS_DIR/usr/share/icons/hicolor/"
fi
# Vivid-Glassy-Dark-Icons is absent from branding/icons; Magna-Glassy-Light is the default theme
copy_if_exists "$BRANDING_DIR/icons/Magna-Glassy-Light-Icons" "$ROOTFS_DIR/usr/share/icons/Magna-Glassy-Light-Icons"

echo "  - Cursor themes..."
copy_if_exists "$BRANDING_DIR/cursors/oreo_white_cursors" "$ROOTFS_DIR/usr/share/icons/oreo_white_cursors"
copy_if_exists "$BRANDING_DIR/cursors/Bibata-Modern-Ice-Regular-Windows" "$ROOTFS_DIR/usr/share/icons/Bibata-Modern-Ice-Regular-Windows"
copy_if_exists "$BRANDING_DIR/cursors/Bibata-Modern-Ice-Large-Windows" "$ROOTFS_DIR/usr/share/icons/Bibata-Modern-Ice-Large-Windows"
copy_if_exists "$BRANDING_DIR/cursors/Bibata-Modern-Ice-Extra-Large-Windows" "$ROOTFS_DIR/usr/share/icons/Bibata-Modern-Ice-Extra-Large-Windows"

echo "  - GTK theme (PurPurDay)..."
copy_if_exists "$BRANDING_DIR/gtk-themes/PurPurDay-GTK" "$ROOTFS_DIR/usr/share/themes/PurPurDay-GTK"

echo "  - Plasma look-and-feel (PurPurDay)..."
copy_if_exists "$BRANDING_DIR/plasma-themes/PurPurDay-Global-6" "$ROOTFS_DIR/usr/share/plasma/look-and-feel/PurPurDay-Global-6"
copy_if_exists "$BRANDING_DIR/plasma-themes/PurPurDay-Splash-6" "$ROOTFS_DIR/usr/share/plasma/look-and-feel/PurPurDay-Splash-6"

echo "  - Plasma desktop theme (PurPurDay)..."
copy_if_exists "$BRANDING_DIR/plasma-themes/PurPurDay-Plasma" "$ROOTFS_DIR/usr/share/plasma/desktoptheme/PurPurDay-Plasma"

echo "  - Color scheme..."
# Prefer explicit colour scheme assets
if [[ -f "$BRANDING_DIR/colourscheme/PurPurDayColor.colors" ]]; then
    sudo mkdir -p "$ROOTFS_DIR/usr/share/color-schemes"
    sudo cp "$BRANDING_DIR/colourscheme/PurPurDayColor.colors" "$ROOTFS_DIR/usr/share/color-schemes/PurPurDayColor.colors"
elif [[ -f "$BRANDING_DIR/plasma-themes/PurPurDay-Plasma/colors" ]]; then
    sudo mkdir -p "$ROOTFS_DIR/usr/share/color-schemes"
    sudo cp "$BRANDING_DIR/plasma-themes/PurPurDay-Plasma/colors" "$ROOTFS_DIR/usr/share/color-schemes/PurPurDayColor.colors"
fi

echo "  - Konsole color scheme..."
if [[ -f "$BRANDING_DIR/colourscheme/PurPurDayBlur-Konsole.colorscheme" ]]; then
    sudo mkdir -p "$ROOTFS_DIR/usr/share/konsole"
    sudo cp "$BRANDING_DIR/colourscheme/PurPurDayBlur-Konsole.colorscheme" "$ROOTFS_DIR/usr/share/konsole/PurPurDayBlur-Konsole.colorscheme"
fi

echo "  - Aurorae window decoration (PurPurDay)..."
copy_if_exists "$BRANDING_DIR/aurorae/PurPurDayBlur-Aurorae-6" "$ROOTFS_DIR/usr/share/aurorae/themes/PurPurDayBlur-Aurorae-6"

# ============================================
# PRODUCT APPLICATION MENU ICONS
# ============================================
# Preserve upstream-owned fallback assets. Product aliases may occupy new paths.
copy_product_icon() {
    local source="$1" relative="$2" owner
    if ! owner="$(sudo chroot "$ROOTFS_DIR" rpm -qf --qf '%{NAME}' "$relative" 2>/dev/null)"; then owner=""; fi
    case "$owner" in
        ''|vigilos-branding) sudo install -Dm0644 "$source" "$ROOTFS_DIR$relative" ;;
        *) printf 'Preserving upstream icon: %s (%s)\n' "$relative" "$owner" ;;
    esac
}
if [[ -f "$BRANDING_DIR/start.svg" ]]; then
    for name in start-here distributor-logo vigilos-start start-here-kde start-here-kde-panel; do
        copy_product_icon "$BRANDING_DIR/start.svg" "/usr/share/icons/hicolor/scalable/apps/$name.svg"
    done
    CONVERT_CMD="$(command -v magick || command -v convert)"
    for size in 16 22 24 32 48 64 96 128 256 512; do
        ICON_DIR="$ROOTFS_DIR/usr/share/icons/hicolor/${size}x${size}/apps"
        sudo mkdir -p "$ICON_DIR"
        sudo "$CONVERT_CMD" -background none "$BRANDING_DIR/start.svg" -resize "${size}x${size}" "$ICON_DIR/vigilos-start.png"
        for name in start-here distributor-logo start-here-kde start-here-kde-panel; do
            copy_product_icon "$ICON_DIR/vigilos-start.png" "/usr/share/icons/hicolor/${size}x${size}/apps/$name.png"
        done
    done
    for name in start-here distributor-logo vigilos-start; do
        copy_product_icon "$BRANDING_DIR/start.svg" "/usr/share/pixmaps/$name.svg"
    done
fi

# Install product-named icons without modifying Fedora-owned upstream artwork.
# Consumers select vigilos-logo through os-release/product theme configuration.
if [[ -f "$BRANDING_DIR/logos/vigilos-logo.png" ]]; then
    for size in 16 22 24 32 48 64 96 128 256 512; do
        ICON_DIR="$ROOTFS_DIR/usr/share/icons/hicolor/${size}x${size}/apps"
        sudo mkdir -p "$ICON_DIR"
        CONVERT_CMD="$(command -v magick || command -v convert)"
        sudo "$CONVERT_CMD" "$BRANDING_DIR/logos/vigilos-logo.png" -resize "${size}x${size}" "$ICON_DIR/vigilos-logo.png"
    done
    sudo install -Dm0644 "$BRANDING_DIR/logos/vigilos-logo.png" "$ROOTFS_DIR/usr/share/pixmaps/vigilos-logo.png"
fi

# ============================================
# USER SKELETON (PurPurDay THEME CONFIG)
# ============================================
echo ""
echo "=== Applying User Skeleton Config (PurPurDay Theme) ==="

# Create skel with PurPurDay theme elements (NOT Global theme - avoids layout issues)
# This applies: Plasma style, icons, cursors, colors, window decoration, splash
# Does NOT apply: Global theme (layout), wallpaper (uses Plasma default)

sudo mkdir -p "$ROOTFS_DIR/etc/skel/.config"

# Copy GTK configs if available
if [[ -d "$SKEL_DIR" ]]; then
    [[ -d "$SKEL_DIR/.config/gtk-3.0" ]] && sudo cp -r "$SKEL_DIR/.config/gtk-3.0" "$ROOTFS_DIR/etc/skel/.config/"
    [[ -d "$SKEL_DIR/.config/gtk-4.0" ]] && sudo cp -r "$SKEL_DIR/.config/gtk-4.0" "$ROOTFS_DIR/etc/skel/.config/"
    [[ -d "$SKEL_DIR/.config/environment.d" ]] && sudo cp -r "$SKEL_DIR/.config/environment.d" "$ROOTFS_DIR/etc/skel/.config/"
    if [[ -f "$SKEL_DIR/.bashrc" ]]; then
        # Keep the signed Fedora bash-owned skeleton intact.
        sudo install -Dm0644 "$SKEL_DIR/.bashrc" "$ROOTFS_DIR/usr/share/vigilos/shell/bashrc"
    fi
    [[ -d "$SKEL_DIR/.local" ]] && sudo cp -r "$SKEL_DIR/.local" "$ROOTFS_DIR/etc/skel/"
fi

# Create Plasma theme configs (individual elements, not Global theme)
echo "  - Creating PurPurDay Plasma configs..."

# plasmarc - Plasma desktop theme
sudo tee "$ROOTFS_DIR/etc/skel/.config/plasmarc" > /dev/null << 'PLASMARC'
[Theme]
name=PurPurDay-Plasma
PLASMARC

# kdeglobals - Icon theme and widget style (NO LookAndFeelPackage!)
sudo tee "$ROOTFS_DIR/etc/skel/.config/kdeglobals" > /dev/null << 'KDEGLOBALS'
[KDE]
widgetStyle=breeze

[Icons]
Theme=Magna-Glassy-Light-Icons

[General]
ColorScheme=PurPurDayColor
BrowserApplication=brave-browser.desktop
KDEGLOBALS

sudo install -Dm0644 "$SKEL_DIR/.config/mimeapps.list" "$ROOTFS_DIR/etc/skel/.config/mimeapps.list"
sudo install -Dm0644 "$SKEL_DIR/.config/kcm-about-distrorc" "$ROOTFS_DIR/etc/skel/.config/kcm-about-distrorc"

# kcminputrc - Cursor theme
sudo tee "$ROOTFS_DIR/etc/skel/.config/kcminputrc" > /dev/null << 'KCMINPUT'
[Mouse]
cursorTheme=oreo_white_cursors
cursorSize=24
KCMINPUT

# kwinrc - Window decoration (Aurorae)
sudo tee "$ROOTFS_DIR/etc/skel/.config/kwinrc" > /dev/null << 'KWINRC'
[org.kde.kdecoration2]
library=org.kde.kwin.aurorae
theme=__aurorae__svg__PurPurDayBlur-Aurorae-6

[Desktops]
Number=1
Rows=1

[DesktopSwitcher]
LayoutName=org.kde.breeze.desktop

[WindowSwitcher]
LayoutName=org.kde.breeze.desktop
KWINRC

# ksplashrc - Splash screen
sudo tee "$ROOTFS_DIR/etc/skel/.config/ksplashrc" > /dev/null << 'KSPLASH'
[KSplash]
Theme=PurPurDay-Splash-6
Engine=KSplashQML
KSPLASH

# Create desktop wallpaper config for Plasma 6
# Use multiple approaches to ensure wallpaper is applied
echo "  - Setting VIGILOS wallpaper as default..."

# Method 1: Desktop containment config
sudo tee "$ROOTFS_DIR/etc/skel/.config/plasma-org.kde.plasma.desktop-appletsrc" > /dev/null << 'PLASMADESKTOP'
[Containments][1]
activityId=
formfactor=0
immutability=1
lastScreen=0
location=0
plugin=org.kde.plasma.folder
wallpaperplugin=org.kde.image

[Containments][1][Wallpaper][org.kde.image][General]
Image=/usr/share/wallpapers/F44/
PreviewImage=/usr/share/vigilos/wallpapers/VIGILOS/contents/images/1672x941.png
SlidePaths=/usr/share/wallpapers/
PLASMADESKTOP

# A minimal product look-and-feel selects wallpaper without replacing panel layouts
# or modifying the upstream plasma-desktop shell-defaults file.
VIGIL_BUILD_GUEST=1 python3 "$BUILD_DIR/scripts/lib/prepare-desktop-defaults.py" "$ROOTFS_DIR" "$BRANDING_DIR"
sudo chroot "$ROOTFS_DIR" kwriteconfig6 --file /etc/skel/.config/kdeglobals --group KDE --key LookAndFeelPackage org.vigilos.desktop

# Explicit product lock-screen defaults; preserve upstream wallpaper packages.
sudo install -m0644 "$SKEL_DIR/.config/kscreenlockerrc" "$ROOTFS_DIR/etc/skel/.config/kscreenlockerrc"


# Copy configs to liveuser
if [[ -d "$ROOTFS_DIR/home/liveuser" ]]; then
    echo "  - Setting up liveuser with PurPurDay theme..."
    sudo mkdir -p "$ROOTFS_DIR/home/liveuser/.config"
    sudo cp "$ROOTFS_DIR/etc/skel/.config/plasmarc" "$ROOTFS_DIR/home/liveuser/.config/"
    sudo cp "$ROOTFS_DIR/etc/skel/.config/kdeglobals" "$ROOTFS_DIR/home/liveuser/.config/"
    sudo cp "$ROOTFS_DIR/etc/skel/.config/mimeapps.list" "$ROOTFS_DIR/home/liveuser/.config/"
    sudo cp "$ROOTFS_DIR/etc/skel/.config/kcm-about-distrorc" "$ROOTFS_DIR/home/liveuser/.config/"
    sudo cp "$ROOTFS_DIR/etc/skel/.config/kcminputrc" "$ROOTFS_DIR/home/liveuser/.config/"
    sudo cp "$ROOTFS_DIR/etc/skel/.config/kwinrc" "$ROOTFS_DIR/home/liveuser/.config/"
    sudo cp "$ROOTFS_DIR/etc/skel/.config/ksplashrc" "$ROOTFS_DIR/home/liveuser/.config/"
    sudo cp "$ROOTFS_DIR/etc/skel/.config/plasma-org.kde.plasma.desktop-appletsrc" "$ROOTFS_DIR/home/liveuser/.config/"
    sudo cp "$ROOTFS_DIR/etc/skel/.config/konsolerc" "$ROOTFS_DIR/home/liveuser/.config/" 2>/dev/null || true

    # Copy GTK configs too
    [[ -d "$ROOTFS_DIR/etc/skel/.config/gtk-3.0" ]] && sudo cp -r "$ROOTFS_DIR/etc/skel/.config/gtk-3.0" "$ROOTFS_DIR/home/liveuser/.config/"
    [[ -d "$ROOTFS_DIR/etc/skel/.config/gtk-4.0" ]] && sudo cp -r "$ROOTFS_DIR/etc/skel/.config/gtk-4.0" "$ROOTFS_DIR/home/liveuser/.config/"

    # Copy .dmrc for session selection
    [[ -f "$ROOTFS_DIR/etc/skel/.dmrc" ]] && sudo cp "$ROOTFS_DIR/etc/skel/.dmrc" "$ROOTFS_DIR/home/liveuser/"

    # Copy Konsole profile
    sudo mkdir -p "$ROOTFS_DIR/home/liveuser/.local/share/konsole"
    [[ -f "$ROOTFS_DIR/etc/skel/.local/share/konsole/VIGILOS.profile" ]] && sudo cp "$ROOTFS_DIR/etc/skel/.local/share/konsole/VIGILOS.profile" "$ROOTFS_DIR/home/liveuser/.local/share/konsole/"

    sudo chroot "$ROOTFS_DIR" chown -R liveuser:liveuser /home/liveuser
fi

echo "  - Theme configs created (Plasma style, icons, cursors, decoration, splash)"

# NOTE: Removed autostart layout application - it was breaking the working panel setup
# The panel is already configured correctly via Plasma defaults + skel configs
echo "  - Panel configured via Plasma defaults (no autostart override needed)"

# Konsole profile with VIGILOS colors
sudo mkdir -p "$ROOTFS_DIR/etc/skel/.local/share/konsole"
sudo tee "$ROOTFS_DIR/etc/skel/.local/share/konsole/VIGILOS.profile" >/dev/null <<'KONSOLE_PROFILE'
[Appearance]
ColorScheme=PurPurDayBlur-Konsole
Opacity=1

[General]
Name=VIGIL OS
Parent=FALLBACK/
KONSOLE_PROFILE

sudo mkdir -p "$ROOTFS_DIR/etc/skel/.config"
sudo tee "$ROOTFS_DIR/etc/skel/.config/konsolerc" >/dev/null <<'KONSOLE_RC'
[Favorite Profiles]
Favorites=VIGILOS.profile

[General]
DefaultProfile=VIGILOS.profile
KONSOLE_RC

# ============================================
# SESSION AND DESKTOP HINTS
# ============================================
echo ""
echo "=== Configuring Session Defaults ==="

# Desktop preference
sudo mkdir -p "$ROOTFS_DIR/etc/sysconfig"
echo "PREFERRED=plasma" | sudo tee "$ROOTFS_DIR/etc/sysconfig/desktop" >/dev/null 2>&1

# Create .dmrc for skel (new users get this)
sudo tee "$ROOTFS_DIR/etc/skel/.dmrc" >/dev/null <<'DMRC'
[Desktop]
Session=plasma
DMRC

# AccountsService for liveuser
sudo mkdir -p "$ROOTFS_DIR/var/lib/AccountsService/users"
sudo tee "$ROOTFS_DIR/var/lib/AccountsService/users/liveuser" >/dev/null <<'ACCT'
[User]
Session=plasma
XSession=plasma
Icon=/usr/share/pixmaps/vigilos-logo.png
SystemAccount=false
ACCT

# AGGRESSIVELY remove/disable GNOME sessions to prevent installer from selecting them
echo "  - Removing GNOME session files..."
for gnome_session in gnome gnome-xorg gnome-classic gnome-classic-xorg gnome-wayland; do
    # Remove X sessions
    sudo rm -f "$ROOTFS_DIR/usr/share/xsessions/${gnome_session}.desktop" 2>/dev/null || true
    # Remove Wayland sessions
    sudo rm -f "$ROOTFS_DIR/usr/share/wayland-sessions/${gnome_session}.desktop" 2>/dev/null || true
done

# Also remove any remaining GNOME session files
sudo rm -f "$ROOTFS_DIR/usr/share/xsessions/gnome"*.desktop 2>/dev/null || true
sudo rm -f "$ROOTFS_DIR/usr/share/wayland-sessions/gnome"*.desktop 2>/dev/null || true

# Disable GNOME initial setup and tour
sudo rm -f "$ROOTFS_DIR/etc/xdg/autostart/gnome-initial-setup-first-login.desktop" 2>/dev/null || true
sudo rm -f "$ROOTFS_DIR/etc/xdg/autostart/gnome-welcome-tour.desktop" 2>/dev/null || true
sudo rm -f "$ROOTFS_DIR/etc/xdg/autostart/org.gnome.Tour.desktop" 2>/dev/null || true

# Set system-wide default session via XDG
echo "  - Setting system-wide default session to Plasma..."
sudo mkdir -p "$ROOTFS_DIR/etc/X11/xinit/Xsession.d"
echo "PREFERRED=plasma" | sudo tee "$ROOTFS_DIR/etc/X11/xinit/Xsession.d/50-default-session" >/dev/null

# Create AccountsService defaults for new users
sudo mkdir -p "$ROOTFS_DIR/etc/accountsservice/user-templates"
sudo tee "$ROOTFS_DIR/etc/accountsservice/user-templates/standard" >/dev/null <<'ACCT_TEMPLATE'
[User]
Session=plasma
XSession=plasma
SystemAccount=false
ACCT_TEMPLATE

# Also create a default user template
sudo tee "$ROOTFS_DIR/var/lib/AccountsService/users/default" >/dev/null <<'ACCT_DEFAULT'
[User]
Session=plasma
XSession=plasma
SystemAccount=false
ACCT_DEFAULT

# ============================================
# INSTALLER SHORTCUT
# ============================================
echo ""
echo "=== Creating Installer Shortcut ==="

sudo tee "$ROOTFS_DIR/usr/share/applications/vigilos-installer.desktop" > /dev/null << 'INSTALLER_EOF'
[Desktop Entry]
Name=Install VIGIL OS
Comment=Install VIGIL OS to your hard drive
Exec=/usr/bin/liveinst
Icon=vigilos-logo
Terminal=false
Type=Application
Categories=System;
StartupNotify=true
StartupWMClass=liveinst
INSTALLER_EOF

# Hide the upstream application-menu entry through an XDG override; preserve
# the upstream-owned file and use our separate product desktop ID.
sudo mkdir -p "$ROOTFS_DIR/usr/local/share/applications"
sudo tee "$ROOTFS_DIR/usr/local/share/applications/liveinst.desktop" >/dev/null <<'HIDE_UPSTREAM_INSTALLER'
[Desktop Entry]
Type=Application
Hidden=true
HIDE_UPSTREAM_INSTALLER

# Add to desktop for live user
sudo mkdir -p "$ROOTFS_DIR/etc/skel/Desktop"
sudo cp "$ROOTFS_DIR/usr/share/applications/vigilos-installer.desktop" "$ROOTFS_DIR/etc/skel/Desktop/"
sudo chmod +x "$ROOTFS_DIR/etc/skel/Desktop/vigilos-installer.desktop"

if [[ -d "$ROOTFS_DIR/home/liveuser/Desktop" ]]; then
    sudo cp "$ROOTFS_DIR/usr/share/applications/vigilos-installer.desktop" "$ROOTFS_DIR/home/liveuser/Desktop/"
    sudo chmod +x "$ROOTFS_DIR/home/liveuser/Desktop/vigilos-installer.desktop"
fi

# ============================================
# OS RELEASE BRANDING
# ============================================
echo ""
echo "=== Applying OS Branding ==="

# Canonical os-release lives in /usr/lib (shipped by fedora-release). We MUST
# overwrite it there, not just /etc, or systemd tooling that reads the canonical
# /usr/lib/os-release will still report "Fedora". /etc/os-release then points to it.
sudo mkdir -p "$ROOTFS_DIR/usr/lib"
sudo tee "$ROOTFS_DIR/usr/lib/os-release" > /dev/null << 'EOF'
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
DEVELOPER="Brad Heffernan"
EOF
if [[ "$DESKTOP" == i3 ]]; then
    sudo sed -i 's/^VARIANT=.*/VARIANT="i3"/;s/^VARIANT_ID=.*/VARIANT_ID=i3/' "$ROOTFS_DIR/usr/lib/os-release"
fi
# /etc/os-release is conventionally a relative symlink to the canonical file.
sudo ln -sf ../usr/lib/os-release "$ROOTFS_DIR/etc/os-release"

# Keep Fedora-owned /etc/system-release and /usr/lib/fedora-release as base compatibility metadata.
echo "VIGIL OS release 1.2 (Loopback)" | sudo tee "$ROOTFS_DIR/etc/vigilos-release" > /dev/null

# Console login banners (otherwise inherited from fedora-release / setup pkgs).
sudo rm -f "$ROOTFS_DIR/etc/issue" "$ROOTFS_DIR/etc/issue.net"
printf 'VIGIL OS 1.2 (Loopback) \\r (\\l)\n\n' | sudo tee "$ROOTFS_DIR/etc/issue" > /dev/null
printf 'VIGIL OS 1.2 (Loopback)\n' | sudo tee "$ROOTFS_DIR/etc/issue.net" > /dev/null

sudo tee "$ROOTFS_DIR/etc/lsb-release" > /dev/null << 'EOF'
DISTRIB_ID="VIGIL OS"
DISTRIB_RELEASE=1.2
DISTRIB_CODENAME=loopback
DISTRIB_DESCRIPTION="VIGIL OS 1.2 (Loopback)"
DISTRIB_DEVELOPER="Brad Heffernan"
EOF

# ============================================
# ANACONDA INSTALLER PROFILE  (bootloader-install fix)
# ============================================
# Fedora 44's Anaconda picks its profile (/etc/anaconda/profile.d/*.conf) by
# matching the live env's os-release ID/VARIANT_ID. Because we rebrand ID=vigilos
# above, NO stock profile matches, so Anaconda falls back to built-in defaults
# where [Bootloader] efi_dir = "default". At the bootloader step it then runs
#   gen_grub_cfgstub /boot/grub2 /boot/efi/EFI/default
# but shim/grub2-efi installed to /boot/efi/EFI/fedora, so EFI/default does not
# exist and the script fails ->
#   org.fedoraproject.Anaconda.BootloaderInstallationError: gen_grub_cfgstub script failed
# (the exact install crash we hit on the RTX 4080 box, 2026-05-31).
#
# Ship an vigilos profile that inherits the fedora profile. Inheritance pulls in
# efi_dir=fedora (and Fedora's storage/bootloader defaults), and [Profile Detection]
# os_id=vigilos makes Anaconda auto-select it from our rebranded os-release.
sudo mkdir -p "$ROOTFS_DIR/etc/anaconda/profile.d"
sudo tee "$ROOTFS_DIR/etc/anaconda/profile.d/vigilos.conf" > /dev/null << 'EOF'
# VIGILOS Anaconda profile — inherits Fedora so the installed system's GRUB
# lands in /boot/efi/EFI/fedora (matching the shim/grub2-efi packages).
[Profile]
profile_id = vigilos
base_profile = fedora

[Profile Detection]
os_id = vigilos

[User Interface]
# Use Anaconda's supported arbitrary-command engine with an isolated Brave app profile.
webui_web_engine = /usr/local/libexec/vigilos-anaconda-browser
custom_stylesheet = /usr/share/vigilos/anaconda/vigilos.css
EOF

# Anaconda reads product/version from /.buildstamp independently of os-release.
sudo python3 - "$ROOTFS_DIR/.buildstamp" <<'BUILDSTAMP_PY'
import configparser,pathlib,sys
p=pathlib.Path(sys.argv[1]);c=configparser.ConfigParser();c.read(p)
if not c.has_section('Main'):c.add_section('Main')
c['Main']['Product']='VIGIL OS';c['Main']['Version']='1.2';c['Main']['IsFinal']='False'
with p.open('w') as f:c.write(f)
BUILDSTAMP_PY
sudo mkdir -p "$ROOTFS_DIR/usr/share/vigilos/anaconda"
sudo tee "$ROOTFS_DIR/usr/share/vigilos/anaconda/vigilos.css" >/dev/null <<'INSTALLER_CSS'
/* VIGIL OS product styling; upstream Anaconda notices remain intact. */
.logo-sidebar { background-image: none; background-color: #111827; }
.logo { background-image: url('/usr/share/vigilos/logos/vigilos-logo-full.png'); background-repeat: no-repeat; background-position: center 20px; background-size: 180px auto; }
.product-logo { background-image: none; }
AnacondaSpokeWindow #nav-box { background-image: none; background-color: #1763ef; color: white; }
INSTALLER_CSS

# WebUI uses Cockpit's product branding selected by os-release ID.
# Keep the upstream HTML/JavaScript and its legal notices unchanged.
sudo mkdir -p "$ROOTFS_DIR/usr/share/cockpit/branding/vigilos"
sudo cp "$BRANDING_DIR/logos/vigilos-logo.png" "$ROOTFS_DIR/usr/share/cockpit/branding/vigilos/logo.png"
sudo cp "$BRANDING_DIR/logos/vigilos-logo-full.png" "$ROOTFS_DIR/usr/share/cockpit/branding/vigilos/brand-large.png"
# Cockpit falls back to the upstream favicon unless product branding supplies one.
sudo install -m0644 "$BRANDING_DIR/logos/vigilos-icon-16.png" "$ROOTFS_DIR/usr/share/cockpit/branding/vigilos/favicon.ico"
sudo tee "$ROOTFS_DIR/usr/share/cockpit/branding/vigilos/branding.css" >/dev/null <<'COCKPIT_CSS'
/* VIGIL OS product styling. Upstream Cockpit/Anaconda licenses are retained. */
#badge { inline-size: 80px; block-size: 80px; background: url("logo.png") center / contain no-repeat; }
#brand::before { content: "VIGIL OS"; }
.anaconda { --brand-default-light: #6397ff; --brand-default: #1763ef; --brand-default-dark: #1248b3; }
.anaconda .logo { background: url("logo.png") center / contain no-repeat; }
/* The upstream feedback QR routes remix reports to Fedora; no remix endpoint is configured. */
.anaconda .feedback-section { display: none !important; }
:not(.pf-v6-theme-dark) .anaconda { --pf-t--global--color--brand--default: var(--brand-default); --pf-t--global--color--brand--hover: var(--brand-default-dark); }
.pf-v6-theme-dark .anaconda { --pf-t--global--color--brand--default: var(--brand-default-light); --pf-t--global--color--brand--hover: var(--brand-default); }
COCKPIT_CSS

# Set dnf releasever for Fedora 44 repos
sudo mkdir -p "$ROOTFS_DIR/etc/dnf/vars"
echo "44" | sudo tee "$ROOTFS_DIR/etc/dnf/vars/releasever" > /dev/null

# Default hostname (installed system should not keep localhost-live)
echo "localhost" | sudo tee "$ROOTFS_DIR/etc/hostname" >/dev/null

# ============================================
# SELINUX MODE
# ============================================
echo ""
echo "=== Configuring SELinux ==="
# Keep the Fedora security default; label changed files in the build instead
# of scheduling a whole-system relabel at the user's second boot.
if [[ -f "$ROOTFS_DIR/etc/selinux/config" ]]; then
    sudo sed -i 's/^SELINUX=.*/SELINUX=enforcing/' "$ROOTFS_DIR/etc/selinux/config"
    sudo sed -i 's/^SELINUXTYPE=.*/SELINUXTYPE=targeted/' "$ROOTFS_DIR/etc/selinux/config"
fi
sudo rm -f "$ROOTFS_DIR/.autorelabel"

# Pre-label key branding paths to minimize live issues
echo "  - Restoring SELinux contexts on branding files..."
if [[ -x "$ROOTFS_DIR/usr/sbin/restorecon" ]]; then
    sudo chroot "$ROOTFS_DIR" restorecon -R /usr/share/plymouth 2>/dev/null || true
    sudo chroot "$ROOTFS_DIR" restorecon -R /usr/share/icons 2>/dev/null || true
    sudo chroot "$ROOTFS_DIR" restorecon -R /usr/share/sddm 2>/dev/null || true
    sudo chroot "$ROOTFS_DIR" restorecon -R /usr/share/wallpapers 2>/dev/null || true
    sudo chroot "$ROOTFS_DIR" restorecon -R /usr/share/themes 2>/dev/null || true
    sudo chroot "$ROOTFS_DIR" restorecon -R /usr/share/color-schemes 2>/dev/null || true
    sudo chroot "$ROOTFS_DIR" restorecon -R /usr/share/aurorae 2>/dev/null || true
    sudo chroot "$ROOTFS_DIR" restorecon -R /usr/share/plasma 2>/dev/null || true
    sudo chroot "$ROOTFS_DIR" restorecon -R /boot 2>/dev/null || true
    sudo chroot "$ROOTFS_DIR" restorecon -R /etc 2>/dev/null || true
    sudo chroot "$ROOTFS_DIR" restorecon -RF /home/liveuser /usr/local /usr/share/vigilos /var/lib/vigilos 2>/dev/null || true
fi


# Configure the installed boot presentation before the very first reboot.
sudo install -m0755 "$BUILD_DIR/scripts/runtime/vigilos-configure-installed-boot" "$ROOTFS_DIR/usr/local/libexec/vigilos-configure-installed-boot"
sudo mkdir -p "$ROOTFS_DIR/usr/share/vigilos/anaconda"
sudo cp "$BUILD_DIR/kickstarts/vigilos-post.ks" "$ROOTFS_DIR/usr/share/vigilos/anaconda/"
# Fedora44 loads interactive defaults before distributing kickstart to D-Bus.
# The later post-scripts append is not propagated to the new runtime module.
if ! grep -q '^%include /usr/share/vigilos/anaconda/vigilos-post.ks$' "$ROOTFS_DIR/usr/share/anaconda/interactive-defaults.ks"; then
    printf '\n%%include /usr/share/vigilos/anaconda/vigilos-post.ks\n' | sudo tee -a "$ROOTFS_DIR/usr/share/anaconda/interactive-defaults.ks" >/dev/null
fi

# Replace Fedora's optional Welcome Center customization package via our RPM.
# Keep the KDE onboarding content and avoid exposing untested third-party toggles.
sudo mkdir -p "$ROOTFS_DIR/usr/share/plasma/plasma-welcome"
sudo cp "$BRANDING_DIR/plasma-welcome/intro-customization.desktop" "$ROOTFS_DIR/usr/share/plasma/plasma-welcome/"
sudo mkdir -p "$ROOTFS_DIR/etc/skel/.config/autostart" "$ROOTFS_DIR/home/liveuser/.config/autostart"
sudo cp "$SKEL_DIR/.config/autostart/imsettings-start.desktop" "$ROOTFS_DIR/etc/skel/.config/autostart/"
sudo cp "$SKEL_DIR/.config/autostart/imsettings-start.desktop" "$ROOTFS_DIR/home/liveuser/.config/autostart/"
sudo chroot "$ROOTFS_DIR" chown -R liveuser:liveuser /home/liveuser/.config/autostart

# Read-only source media can expose copied directories as0555. User defaults
# must remain writable by their eventual owner, including inherited subdirs.
sudo chmod -R u+rwX "$ROOTFS_DIR/etc/skel"
if [[ -d "$ROOTFS_DIR/home/liveuser" ]]; then
    sudo chmod -R u+rwX "$ROOTFS_DIR/home/liveuser"
fi

if [[ "$DESKTOP" == i3 ]]; then
    sudo env VIGIL_BUILD_GUEST=1 bash "$BUILD_DIR/scripts/lib/install-i3.sh" "$ROOTFS_DIR" "$WORK_DIR"
fi
printf "%s\n" "$DESKTOP" | sudo tee "$ROOTFS_DIR/etc/vigilos-desktop" >/dev/null
sudo env VIGIL_BUILD_GUEST=1 VIGIL_DESKTOP="$DESKTOP" bash "$BUILD_DIR/scripts/lib/package-branding.sh" "$ROOTFS_DIR" "$WORK_DIR"

# ============================================
# UPDATE ICON CACHES
# ============================================
echo ""
echo "=== Updating Icon Caches ==="
if [[ -x "$ROOTFS_DIR/usr/bin/gtk-update-icon-cache" ]]; then
    sudo chroot "$ROOTFS_DIR" gtk-update-icon-cache -f /usr/share/icons/hicolor 2>/dev/null || true
    if [[ -d "$ROOTFS_DIR/usr/share/icons/Magna-Glassy-Light-Icons" ]]; then
        sudo chroot "$ROOTFS_DIR" gtk-update-icon-cache -f /usr/share/icons/Magna-Glassy-Light-Icons 2>/dev/null || true
    fi
fi
if [[ -x "$ROOTFS_DIR/usr/bin/kbuildsycoca6" ]]; then
    sudo chroot "$ROOTFS_DIR" kbuildsycoca6 --noincremental 2>/dev/null || true
fi

# ============================================
# MODIFY INITRD FOR BOOT SPLASH
# ============================================
echo ""
echo "=== Modifying initrd for boot splash ==="

INITRD_PATH=""
for candidate in "$WORK_DIR/new_iso/boot/x86_64/loader/initrd" "$WORK_DIR/new_iso/images/pxeboot/initrd.img"; do
    [[ ! -f "$candidate" ]] || { INITRD_PATH="$candidate"; break; }
done
[[ -n "$INITRD_PATH" ]] || { echo 'ERROR: Live initramfs path not found.' >&2; exit 1; }
KERNEL_VERSION="$(sudo find "$ROOTFS_DIR/usr/lib/modules" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort -V | tail -1)"
[[ -n "$KERNEL_VERSION" ]] || { echo 'ERROR: Live kernel modules missing.' >&2; exit 1; }
# An updated root must boot its matching kernel, not the original ISO kernel.
LIVE_KERNEL="$ROOTFS_DIR/boot/vmlinuz-$KERNEL_VERSION"
[[ -f "$LIVE_KERNEL" ]] || { echo "ERROR: Matching kernel missing: $KERNEL_VERSION" >&2; exit 1; }
sudo cp "$LIVE_KERNEL" "$WORK_DIR/new_iso/boot/x86_64/loader/linux"
# Rebuild with dracut instead of assuming a single xz cpio archive. Keep generic
# hardware support and omit the unused livenet hook that caused the recorded pause.
sudo chroot "$ROOTFS_DIR" dracut --force --no-hostonly --no-hostonly-cmdline --compress "zstd -3 -q -T1" --add 'dmsquash-live plymouth' --omit livenet /tmp/vigil-live-initrd.img "$KERNEL_VERSION"
sudo cp "$ROOTFS_DIR/tmp/vigil-live-initrd.img" "$INITRD_PATH"
sudo rm -f "$ROOTFS_DIR/tmp/vigil-live-initrd.img"


# ============================================
# UNMOUNT BIND MOUNTS (chroot operations done)
# ============================================
echo ""
echo "Restoring portable image state..."
sudo chroot "$ROOTFS_DIR" dnf clean all
sudo rm -f "$ROOTFS_DIR/etc/resolv.conf"
if [[ -e "$WORK_DIR/resolv.conf.original" || -L "$WORK_DIR/resolv.conf.original" ]]; then
    sudo cp -a "$WORK_DIR/resolv.conf.original" "$ROOTFS_DIR/etc/resolv.conf"
fi
sudo rm -f "$ROOTFS_DIR/etc/machine-id"
printf "" | sudo tee "$ROOTFS_DIR/etc/machine-id" >/dev/null
echo "Unmounting chroot bind mounts..."
sync
sudo umount -l "$ROOTFS_DIR/run" 2>/dev/null || true
sudo umount -l "$ROOTFS_DIR/sys" 2>/dev/null || true
sudo umount -l "$ROOTFS_DIR/proc" 2>/dev/null || true
sudo umount -l "$ROOTFS_DIR/dev" 2>/dev/null || true
sleep 1

# Verify mounts released
if mountpoint -q "$ROOTFS_DIR/dev"; then
    echo 'ERROR: A chroot bind mount remains active; preserving work directory.' >&2
    exit 1
fi

# The current verified Fedora KDE pipeline uses a flat EROFS root. Keep its
# finalization in one reusable, guarded stage so a packaging failure can be
# retried without repeating a successful base update or changing old outputs.
if [[ "$ROOT_IMAGE_FORMAT" != *EROFS* || "$MOUNTED_ROOTFS" == true ]]; then
    echo 'ERROR: This verified pipeline requires the official Fedora 44 KDE EROFS base.' >&2
    exit 1
fi
# Preserve the BIOS core image, and supply its optional graphical modules from
# the same signed Fedora GRUB package already present in the prepared target.
if [[ -d "$ROOTFS_DIR/usr/lib/grub/i386-pc" ]]; then
    sudo mkdir -p "$WORK_DIR/new_iso/boot/grub2/i386-pc"
    for module in "$ROOTFS_DIR/usr/lib/grub/i386-pc/"*.mod "$ROOTFS_DIR/usr/lib/grub/i386-pc/"*.lst; do
        [[ -f "$module" ]] && sudo cp -a "$module" "$WORK_DIR/new_iso/boot/grub2/i386-pc/"
    done
fi

sudo env VIGIL_BUILD_GUEST=1 bash "$BUILD_DIR/scripts/lib/finish-prepared-image.sh" "$WORK_DIR" "$input_iso" "$output_iso" "$ISO_LABEL"
