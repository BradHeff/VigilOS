> **Isolated development candidate:** Source validation and development RPM builds have passed; ISO/VM acceptance testing is in progress. Read docs/ISOLATED-TEST-PLAN.md and the lab evidence for actual results. Historical release/test statements below describe prior work. The current first pass uses official Fedora repositories, defers automatic third-party drivers/apps, and retains RPM/DNF5 updates. VpM remains a design proposal. The relettered city wallpaper is native 1672×941; larger build exports are upscaled derivatives.

<p align="center">
  <img src="branding/logos/vigilos-logo.png" alt="VIGILOS Logo" width="200"/>
</p>

<h1 align="center">VIGIL OS</h1>

<p align="center">
  <strong>A Modern, Elegant Linux Distribution Built for Performance and Beauty</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#screenshots">Screenshots</a> •
  <a href="#installation">Installation</a> •
  <a href="#package-management">Package Management</a> •
  <a href="#building">Building</a> •
  <a href="#contributing">Contributing</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.2-blue?style=for-the-badge" alt="Version"/>
  <img src="https://img.shields.io/badge/base-Fedora%2044-51A2DA?style=for-the-badge" alt="Base"/>
  <img src="https://img.shields.io/badge/desktop-KDE%20Plasma%206-1D99F3?style=for-the-badge" alt="Desktop"/>
  <img src="https://img.shields.io/badge/license-GPL--3.0-green?style=for-the-badge" alt="License"/>
</p>

---

## Overview

**VIGIL OS 1.2 "Loopback"** is a Linux distribution based on Fedora 44, featuring the KDE Plasma 6 desktop environment. Built for IT engineers and power users, it pairs the stability and security of Fedora with a cohesive custom visual identity and a sensible default toolset.

Whether you're a sysadmin, network engineer, developer, or power user, VIGILOS provides a polished, cohesive experience right out of the box.

> **Release codename:** `Loopback` (`VERSION_CODENAME=loopback`). Current development candidate: **VIGIL OS 1.2 "Loopback"**. Prior stable-release claims are historical and do not certify this candidate. The codename stays `Loopback` across point releases.

---

## Features

### Desktop Experience

| Feature | Description |
|---------|-------------|
| **KDE Plasma 6** | KDE Plasma Wayland flagship; X11 is not part of the acceptance claim |
| **PurPurDay Theme** | Custom global theme with matching colors, icons, and decorations |
| **Magna-Glassy Icons** | Beautiful glassy icon theme for a modern look |
| **Oreo Cursors** | Elegant white cursor theme |
| **Custom Plymouth** | VIGILOS branded boot splash |
| **SDDM Theme** | Matching login screen with VIGILOS branding |
| **GRUB Theme** | Custom bootloader theme |

### System Features

- **Fedora 44 Base** — Latest packages, cutting-edge kernel, and excellent hardware support
- **SELinux** — Live and installed boots retain enforcing mode. The upstream live installer temporarily relaxes enforcement while installing and restores it on normal exit.
- **Flatpak** — Available for user-managed applications; this official-repositories-first candidate does not automatically install Flathub applications.
- **DNF Package Manager** — Fast, reliable package management
- **Systemd** — Modern init system with excellent service management
- **Storage** — The actual guided Anaconda install uses Btrfs for root/home, ext4 for /boot, and a FAT EFI partition on UEFI.

### Pre-installed Applications

| Category | Applications |
|----------|-------------|
| **Web** | Firefox |
| **Office** | LibreOffice Suite |
| **Files** | Dolphin File Manager |
| **Terminal** | Konsole with custom VIGILOS profile |
| **Text Editor** | Kate |
| **Images** | Gwenview |
| **Documents** | Okular |
| **Archive** | Ark |
| **Screenshots** | Spectacle |
| **Remote Desktop** | Remmina (RDP, VNC, SPICE) |
| **System** | Plasma Discover, System Monitor |

---

## Screenshots

> Screenshots pending: real captures of the GRUB menu, Plasma desktop, and Anaconda installer will be added here (see CLAUDE.md open follow-ups).

---

## System Requirements

### Minimum Requirements

| Component | Requirement |
|-----------|-------------|
| **Processor** | 64-bit (x86_64) CPU, 2 GHz or faster |
| **Memory** | 4 GB RAM |
| **Storage** | 20 GB available disk space |
| **Graphics** | GPU with OpenGL 3.3 support |
| **Display** | 1024x768 resolution |

### Recommended Requirements

| Component | Requirement |
|-----------|-------------|
| **Processor** | 64-bit quad-core CPU, 3 GHz or faster |
| **Memory** | 8 GB RAM or more |
| **Storage** | 50 GB SSD |
| **Graphics** | GPU with Vulkan support |
| **Display** | 1920x1080 or higher |

---

## Installation

### Download

The verified development ISO and checksums are in the isolated lab output directory. No public release was created or verified by this work.

### Disposable VM testing

Use the isolated lab launchers described in [the acceptance plan](docs/ISOLATED-TEST-PLAN.md).
They attach only owned QCOW2 files and read-only media, serialize VMs and refuse unknown
ownership markers. Physical media writes are outside the executed workflow.

### Installation Process

1. Boot from the USB/DVD
2. Select **"Start VIGILOS"** from the boot menu
3. Once the live desktop loads, click **"Install VIGILOS"** on the desktop
4. Follow the Anaconda installer wizard
5. Reboot and enjoy VIGILOS!

### Live Session

The live environment includes a fully functional KDE Plasma desktop with automatic login. You can explore VIGILOS before installing.

- **Default User:** `liveuser` (no password, passwordless sudo)
- **Session:** Plasma Wayland

---

## Package Management

### Current: DNF (Fedora Package Manager)

VIGILOS currently uses DNF with access to Fedora 44 repositories:

```bash
# Update system
sudo dnf upgrade

# Install a package
sudo dnf install package-name

# Search for packages
dnf search keyword

# Remove a package
sudo dnf remove package-name
```

### Flatpak

Flatpak is pre-installed for sandboxed applications:

```bash
# Add Flathub repository
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

# Install an application
flatpak install flathub org.application.Name

# Run a Flatpak application
flatpak run org.application.Name
```

---

## VpM — VIGILOS Package Manager

<p align="center">
  <img src="https://img.shields.io/badge/status-In%20Development-orange?style=for-the-badge" alt="Status"/>
</p>

### Coming Soon

**VpM is a design proposal in this checkout.** No Rust implementation or native transaction engine is present here. Its proposed features require prototypes, security review and disposable-root tests; the current ISO uses supported RPM/DNF5 updates. See VPM.md for open system-ownership and rollback decisions. Proposed features:

| Feature | Description |
|---------|-------------|
| **Native `.vpm` Packages** | Lightweight, efficient package format designed for VIGILOS |
| **RPM Compatibility** | Planned; RPM-owned system state must remain authoritative in rpmdb until a separate migration is designed |
| **ViR Repository** | Community-driven package repository (like Arch's AUR) |
| **VPMBUILD System** | Simple, readable build scripts for package creation |
| **Rust implementation** | Planned; performance and parallel transactions are unverified |

<p align="center">
  <a href="VPM.md">
    <img src="https://img.shields.io/badge/📖_Read_the_Full_VpM_Documentation-4A90D9?style=for-the-badge" alt="VpM Documentation"/>
  </a>
</p>

> **Want to learn more?** Check out the **[VpM Documentation](VPM.md)** for detailed information on package format, CLI usage, building packages, the ViR repository system, and RPM compatibility.

---

## Building VIGILOS

### Isolated build entry points

The executed route remixes a verified official Fedora 44 KDE ISO, updates the full base
through signed official repositories, creates product-owned development RPMs, regenerates
a matching kernel/initramfs, and packs a clean EROFS root into a hybrid BIOS/UEFI ISO.
Fedora 44 names its EROFS payload `LiveOS/squashfs.img`; it is not SquashFS.

Run build dependencies, mounts and chroots inside a dedicated disposable Fedora builder.
`guest-builder-setup.sh` and `build-and-brand.sh` require the VM marker and explicit
`VIGIL_BUILD_GUEST=1`; the marker is an accidental-host-execution guard. See the
[isolated acceptance plan](docs/ISOLATED-TEST-PLAN.md) for resource and network boundaries.
The osbuild-composer and legacy kickstart alternatives are not the validated release route.

```bash
# Source-only checks (no installation or VM start):
bash scripts/validate.sh
# Inside the already prepared, approved disposable builder only:
VIGIL_BUILD_GUEST=1 bash scripts/build-and-brand.sh /path/to/verified-Fedora-KDE.iso
```

`build-and-brand.sh` creates a fresh output directory and preserves old outputs.
`apply-composer-branding.sh` performs the remix; `package-branding.sh` creates local
unsigned development RPMs while retaining upstream signature policy. `pack-prepared-root.sh`
and `finish-prepared-image.sh` support reviewed recovery of an already prepared build.
The final candidate record identifies any reused prepared root and newly rebuilt parts.

### Project Structure

```
vigilos-build/
├── blueprints/           # osbuild-composer blueprints
│   └── vigilos-kde.toml  # Main KDE Plasma blueprint
├── branding/             # Visual assets
│   ├── logos/            # VIGILOS logos and icons
│   ├── wallpapers/       # Desktop wallpapers
│   ├── plymouth/         # Boot splash theme
│   ├── grub/             # Bootloader theme
│   ├── sddm/             # Login manager theme
│   ├── plasma-themes/    # KDE Plasma themes
│   ├── icons/            # Icon themes
│   └── cursors/          # Cursor themes
├── scripts/              # Build and branding scripts
│   ├── build-iso.sh      # ISO build script
│   └── apply-composer-branding.sh  # Branding application
├── Screenshots/          # OS screenshots for documentation
├── PLASMA-CONFIGS/       # KDE configuration files
├── Skel/                 # User skeleton files
├── VPM.md                # VpM Package Manager documentation
└── README.md             # This file
```

---

## Customization

### Changing Themes

VIGILOS uses KDE Plasma's standard theming system:

1. Open **System Settings**
2. Navigate to **Appearance**
3. Customize:
   - **Global Theme** — Overall look and feel
   - **Plasma Style** — Panel and widget appearance
   - **Colors** — System color scheme
   - **Window Decorations** — Titlebar style
   - **Icons** — Icon theme
   - **Cursors** — Mouse cursor theme

### Wallpapers

Default wallpapers are located in `/usr/share/wallpapers/VIGILOS/`.

To add custom wallpapers, place them in `~/.local/share/wallpapers/`.

---

## Troubleshooting

### Boot Issues

**Black screen after boot:**
- Try booting with the "Basic Graphics" option
- Add `nomodeset` to kernel parameters

**Plymouth not showing:**
- Ensure `rhgb quiet` are in kernel parameters
- Rebuild initramfs: `sudo dracut -f`

### Display Issues

**Wrong resolution:**
- Open System Settings → Display and Monitor
- Configure your display settings

**Wayland issues:**
- Log out and select "Plasma (X11)" from the session menu

### Package Issues

**DNF slow:**
```bash
sudo dnf makecache
```

**Broken dependencies:**
```bash
sudo dnf distro-sync
```

---

## Contributing

We welcome contributions to VIGILOS! Here's how you can help:

### Reporting Issues

- Use the [GitHub Issues](https://github.com/vigilglm/vigilos/issues) page
- Include system information: `fastfetch` or `inxi -F`
- Provide steps to reproduce the issue

### Development

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Areas of Contribution

- **Theming** — Improve or create new visual themes
- **Documentation** — Help improve docs and guides
- **Testing** — Test on different hardware configurations
- **Translations** — Help translate VIGILOS
- **VpM Development** — Contribute to the package manager

---

## Roadmap

### Version 1.2 (Current)
- [x] Universal multi-GPU live boot (NVIDIA RTX 40xx/Ada via nouveau blacklist; AMD/Intel native KMS)
- [x] Automatic proprietary NVIDIA driver install on first boot (installed systems) + reboot prompt
- [x] Everything from 1.0

### Version 1.0
- [x] KDE Plasma 6 desktop
- [x] PurPurDay theme integration
- [x] Custom boot splash and login screen
- [x] GRUB theming
- [x] Pre-installed applications

### Version 1.1 (Planned)
- [ ] VpM package manager (alpha)
- [ ] VIGILOS Welcome application
- [ ] Additional wallpapers
- [ ] Improved installer experience

### Version 2.0 (Future)
- [ ] VpM package manager (stable)
- [ ] ViR community repository
- [ ] VIGILOS-specific applications
- [ ] ARM64 support

---

## Credits

### Developer

**Brad Heffernan** — Creator and Lead Developer

### Acknowledgments

- [Fedora Project](https://fedoraproject.org/) — Base distribution
- [KDE Community](https://kde.org/) — Plasma desktop environment
- [PurPurDay Theme](https://store.kde.org/) — Original theme inspiration
- All open-source contributors whose work makes VIGILOS possible

---

## License

VIGILOS is distributed under the **GNU General Public License v3.0**.

See [LICENSE](LICENSE) for more information.

---

## Links

- **Website:** [https://vigilglm.ai](https://vigilglm.ai)
- **Documentation:** [https://docs.vigilglm.ai](https://docs.vigilglm.ai)
- **Support:** [https://support.vigilglm.ai](https://support.vigilglm.ai)
- **GitHub:** [https://github.com/vigilglm](https://github.com/vigilglm)

---

<p align="center">
  <strong>VIGILOS</strong> — Where Beauty Meets Performance
</p>

<p align="center">
  Made with ❤️ in Australia
</p>
