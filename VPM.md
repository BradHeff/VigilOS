<p align="center">
  <img src="branding/logos/vigilos-logo.png" alt="VpM Logo" width="120"/>
</p>

<h1 align="center">VpM — VIGILOS Package Manager</h1>

<p align="center">
  <strong>A Modern, Fast, and Flexible Package Manager for VIGILOS</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/status-Design%20Proposal-orange?style=for-the-badge" alt="Status"/>
  <img src="https://img.shields.io/badge/language-Rust-B7410E?style=for-the-badge" alt="Language"/>
  <img src="https://img.shields.io/badge/license-GPL--3.0-green?style=for-the-badge" alt="License"/>
</p>

<p align="center">
  <a href="#overview">Overview</a> •
  <a href="#features">Features</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#package-format">Package Format</a> •
  <a href="#usage">Usage</a> •
  <a href="#building-packages">Building Packages</a> •
  <a href="#repository">Repository</a>
</p>

---

## Overview

> **Evidence status:** This checkout contains this design document and no Rust source or Cargo manifests. All VpM features, command examples, architecture and repository endpoints below are proposals, not verified capabilities. The separately linked public GitHub URL returned HTTP 404 during this review; no private access was attempted. The ISO continues to use Fedora RPM/DNF5 for supported system updates.


**VpM (VIGILOS Package Manager)** is a next-generation package manager designed specifically for VIGILOS. Inspired by the simplicity of Arch Linux's `pacman` and the community-driven AUR, VpM combines ease of use with powerful features.

### Design Philosophy

- **Simplicity** — Intuitive commands that feel natural
- **Speed** — Built in Rust for blazing-fast performance
- **Flexibility** — Native `.vpm` packages with RPM compatibility
- **Community** — User-contributed packages via ViR (VIGILOS Package Repository)
- **Transparency** — Clear, readable build scripts

---

## Features

### Core Features

| Feature | Description |
|---------|-------------|
| **Native `.vpm` Format** | Lightweight, efficient package format designed for VIGILOS |
| **RPM Compatibility** | Seamless installation of Fedora/RHEL `.rpm` packages |
| **Parallel Downloads** | Multi-threaded package downloads for faster operations |
| **Dependency Resolution** | Automatic handling of package dependencies |
| **Transaction Safety** | Atomic operations with rollback support |
| **Delta Updates** | Download only changed portions of packages |

### Repository System

| Repository | Description |
|------------|-------------|
| **core** | Essential system packages maintained by VIGILOS team |
| **extra** | Additional software maintained by VIGILOS team |
| **community** | User-contributed packages from ViR |
| **fedora** | Compatibility layer for Fedora RPM repositories |

### Package Sources

```
┌─────────────────────────────────────────────────────────┐
│                    VpM Package Sources                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│   ┌─────────────┐    ┌─────────────┐    ┌────────────┐  │
│   │  .vpm       │    │  .rpm       │    │  ViR       │  │
│   │  (Native)   │    │  (Fedora)   │    │  (Source)  │  │
│   └──────┬──────┘    └──────┬──────┘    └──────┬─────┘  │
│          │                  │                   │        │
│          └──────────────────┴───────────────────┘        │
│                             │                            │
│                    ┌────────▼────────┐                   │
│                    │  VpM Runtime    │                   │
│                    │  (Unified API)  │                   │
│                    └────────┬────────┘                   │
│                             │                            │
│                    ┌────────▼────────┐                   │
│                    │   VIGILOS       │                   │
│                    │   System        │                   │
│                    └─────────────────┘                   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Architecture

### Component Overview

```
vpm/
├── libvpm/              # Core library
│   ├── src/
│   │   ├── package.rs   # Package handling
│   │   ├── repo.rs      # Repository management
│   │   ├── resolve.rs   # Dependency resolution
│   │   ├── download.rs  # Parallel downloader
│   │   ├── install.rs   # Installation logic
│   │   ├── rpm.rs       # RPM compatibility layer
│   │   └── db.rs        # Local database
│   └── Cargo.toml
├── vpm-cli/             # Command-line interface
│   ├── src/
│   │   ├── main.rs
│   │   ├── commands/
│   │   │   ├── install.rs
│   │   │   ├── remove.rs
│   │   │   ├── upgrade.rs
│   │   │   ├── search.rs
│   │   │   ├── query.rs
│   │   │   └── build.rs
│   │   └── config.rs
│   └── Cargo.toml
├── vpm-build/           # Package build system
│   ├── src/
│   │   ├── vpmbuild.rs  # VPMBUILD parser
│   │   ├── builder.rs   # Package builder
│   │   └── compress.rs  # Compression handling
│   └── Cargo.toml
└── vpm-repo/            # Repository tools
    ├── src/
    │   ├── server.rs    # Repo server
    │   └── sync.rs      # Sync utilities
    └── Cargo.toml
```

### Database Structure

The proposal considers SQLite for native VpM package metadata. SQLite transaction atomicity alone does not provide filesystem, package-scriptlet, bootloader or whole-OS rollback. Database design and crash recovery remain unimplemented:

```
/var/lib/vpm/
├── local.db             # Installed packages database
├── sync/                # Synced repository databases
│   ├── core.db
│   ├── extra.db
│   ├── community.db
│   └── fedora.db
├── cache/               # Downloaded packages
│   ├── vpm/
│   └── rpm/
└── logs/                # Transaction logs
```

---

## Package Format

### `.vpm` Package Structure

An `.vpm` package is a compressed archive containing:

```
package-1.0.0-1.vpm
├── .PKGINFO             # Package metadata (TOML format)
├── .MTREE               # File integrity database
├── .INSTALL             # Pre/post install scripts (optional)
└── data/                # Actual package files
    ├── usr/
    │   ├── bin/
    │   ├── lib/
    │   └── share/
    └── etc/
```

### Package Metadata (.PKGINFO)

```toml
[package]
name = "example-app"
version = "1.0.0"
release = 1
description = "An example application for VIGILOS"
url = "https://example.com"
license = "MIT"
arch = "x86_64"

[maintainer]
name = "Developer Name"
email = "dev@example.com"

[dependencies]
runtime = ["glibc>=2.38", "qt6-base"]
optional = ["example-plugins"]

[build]
makedepends = ["cmake", "gcc", "qt6-tools"]

[files]
backup = ["/etc/example/config.toml"]
```

### Compression

VpM packages use **zstd** compression for optimal balance of speed and size:

| Compression | Speed | Size | VpM Default |
|-------------|-------|------|-------------|
| gzip        | Fast  | Large | No |
| xz          | Slow  | Small | No |
| **zstd**    | Fast  | Small | **Yes** |

---

## Usage

### Basic Commands

```bash
# Synchronize package databases
vpm sync

# Update all packages
vpm upgrade

# Install a package
vpm install package-name

# Install from .vpm file
vpm install ./package-1.0.0-1.vpm

# Install RPM package (compatibility mode)
vpm install package.rpm

# Remove a package
vpm remove package-name

# Search for packages
vpm search keyword

# Show package information
vpm info package-name

# List installed packages
vpm list

# List explicitly installed packages
vpm list --explicit

# Clean package cache
vpm clean
```

### Advanced Usage

```bash
# Install without dependencies (not recommended)
vpm install --nodeps package-name

# Download only, don't install
vpm install --downloadonly package-name

# Reinstall a package
vpm install --reinstall package-name

# Remove package and its orphaned dependencies
vpm remove --recursive package-name

# Query files owned by a package
vpm query --files package-name

# Find which package owns a file
vpm query --owns /usr/bin/example

# List packages from a specific repository
vpm list --repo core

# Check for package updates
vpm check-updates
```

### Repository Management

```bash
# List configured repositories
vpm repo list

# Add a repository
vpm repo add myrepo https://repo.example.com/vigilos

# Remove a repository
vpm repo remove myrepo

# Disable a repository temporarily
vpm repo disable fedora

# Enable a repository
vpm repo enable fedora
```

---

## Building Packages

### VPMBUILD File

The `VPMBUILD` file is a shell script that defines how to build a package:

```bash
# Maintainer: Your Name <your.email@example.com>

pkgname=example-app
pkgver=1.0.0
pkgrel=1
pkgdesc="An example application for VIGILOS"
arch=('x86_64')
url="https://github.com/example/app"
license=('MIT')
depends=('glibc' 'qt6-base')
makedepends=('cmake' 'gcc' 'qt6-tools')
source=("https://github.com/example/app/archive/v${pkgver}.tar.gz")
sha256sums=('abc123def456...')

prepare() {
    cd "$srcdir/$pkgname-$pkgver"
    # Apply patches, prepare source
}

build() {
    cd "$srcdir/$pkgname-$pkgver"
    cmake -B build \
        -DCMAKE_INSTALL_PREFIX=/usr \
        -DCMAKE_BUILD_TYPE=Release
    cmake --build build
}

check() {
    cd "$srcdir/$pkgname-$pkgver"
    cmake --build build --target test
}

package() {
    cd "$srcdir/$pkgname-$pkgver"
    DESTDIR="$pkgdir" cmake --install build

    # Install license
    install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
```

### Building a Package

```bash
# Navigate to directory with VPMBUILD
cd ~/packages/example-app

# Build the package
vpm-build

# Build and install
vpm-build --install

# Build with specific architecture
vpm-build --arch x86_64

# Clean build directory
vpm-build --clean
```

### Package Validation

```bash
# Validate package before publishing
vpm-build --check

# Lint VPMBUILD file
vpm-lint VPMBUILD

# Test installation in container
vpm-build --test
```

---

## Repository

### ViR — VIGILOS Package Repository

ViR is the community-driven package repository for VIGILOS, similar to the AUR for Arch Linux.

#### Submitting Packages

1. **Create an ViR account** at [vir.vigilglm.ai](https://vir.vigilglm.ai)

2. **Prepare your package:**
   ```bash
   # Create package directory
   mkdir mypackage && cd mypackage

   # Create VPMBUILD
   vim VPMBUILD

   # Generate .SRCINFO
   vpm-build --geninfo
   ```

3. **Submit to ViR:**
   ```bash
   # Initialize ViR repository
   git init

   # Add ViR remote
   git remote add apr ssh://apr@vir.vigilglm.ai/mypackage.git

   # Push your package
   git push apr main
   ```

#### Installing from ViR

```bash
# Install ViR helper (included by default)
vpm install apr-helper

# Search ViR
apr search package-name

# Install from ViR (builds from source)
apr install package-name

# Update ViR packages
apr upgrade
```

### Repository Configuration

Repository configuration is stored in `/etc/vpm/repos.d/`:

```ini
# /etc/vpm/repos.d/core.conf
[core]
Server = https://repo.vigilglm.ai/$repo/$arch
Enabled = true
SigLevel = Required

# /etc/vpm/repos.d/fedora.conf
[fedora]
Type = rpm
Server = https://mirrors.fedoraproject.org/metalink?repo=fedora-$releasever&arch=$arch
Enabled = true
# Fedora RPM package signatures remain mandatory via upstream RPM/DNF verification.
# Native catalog signature settings do not configure Fedora repository metadata.
```

---

## RPM Compatibility

### How It Works

The following compatibility diagram is an unimplemented proposal, not a safe coexistence design. Extracting RPM payloads, running scriptlets, and recording only SQLite state would bypass RPM ownership and cannot safely coexist with DNF/rpmdb:

```
┌─────────────────────────────────────────────────────────┐
│                   RPM Compatibility Layer                │
├─────────────────────────────────────────────────────────┤
│                                                          │
│   ┌─────────────┐         ┌─────────────────────────┐   │
│   │  .rpm       │   ───►  │  VpM RPM Handler        │   │
│   │  Package    │         │  • Parse RPM spec       │   │
│   └─────────────┘         │  • Convert dependencies │   │
│                           │  • Extract files        │   │
│                           │  • Run scriptlets       │   │
│                           └───────────┬─────────────┘   │
│                                       │                  │
│                           ┌───────────▼─────────────┐   │
│                           │  VpM Database           │   │
│                           │  (Unified tracking)     │   │
│                           └─────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Installing RPM Packages

```bash
# Install RPM from file
vpm install ./package-1.0.0.x86_64.rpm

# Install RPM from Fedora repos
vpm install --repo fedora package-name

# Query RPM package info
vpm info --repo fedora package-name

# List available RPM packages
vpm search --repo fedora keyword
```

### Open ownership decision

No ownership architecture has been selected or implemented. Evaluate explicitly:

1. **Supported Fedora system with isolated native packages:** rpmdb remains authoritative for RPM-owned system files and RPM/DNF5 performs their transactions. Early `.vpm` packages install into a separate prefix, with collision detection and no writes over RPM-owned files. Native metadata can use SQLite without claiming ownership of the Fedora system.
2. **Future VpM sole ownership of the complete root:** requires an explicit migration, replacement of RPM/DNF system management, compatible dependencies/scriptlets/triggers, complete ownership accounting, crash recovery, upgrade and rollback design, security maintenance and repository infrastructure. This is a separate distribution architecture decision.

The ISO first release keeps Fedora updates supported. Do not silently implement either option as a solver/database replacement or treat a branded DNF frontend as completion of the native `.vpm` ambition.

### Signature and recipe trust boundary

Keep upstream Fedora RPM signatures and provenance mandatory. Do not bypass verification or invent native `DatabaseRequired` metadata semantics for Fedora repositories. A native signed catalog/format needs its own specified verification protocol, key lifecycle and revocation policy before it can be trusted.

AI-generated package descriptions, recipes, patches and commands are untrusted inputs. They must never automatically become root commands, trusted signing keys, signature exceptions or approved installation scripts. Build and inspect in disposable roots, retain source/checksum provenance, and require an explicit reviewed transaction boundary.

### Evidence-based prototype sequence

- Specify and implement native `.vpm` archive inspection and deterministic building.
- Define signed catalog verification and test invalid signatures/revocation paths.
- Implement a read-only dependency/ownership planner with explicit conflict reporting.
- Exercise native installs/removals and failure recovery only in disposable roots.
- Decide the system ownership architecture before any mixed live-system transaction support.
- Report measured test results; do not advertise production readiness from design tables.

---

## Configuration

### Main Configuration

`/etc/vpm/vpm.conf`:

```ini
[options]
# Root directory for installation
RootDir = /

# Cache directory for downloads
CacheDir = /var/cache/vpm

# Database directory
DBPath = /var/lib/vpm

# Log file
LogFile = /var/log/vpm.log

# GPG key directory
GPGDir = /etc/vpm/gnupg

# Architecture
Architecture = auto

# Parallel downloads
ParallelDownloads = 5

# Check available disk space
CheckSpace = true

# Default signature verification level
# Proposed native VpM catalog policy only; not a Fedora/DNF configuration option.
SigLevel = Required DatabaseRequired

[colors]
# Enable colored output
Color = auto
```

### Mirror Configuration

`/etc/vpm/mirrorlist`:

```
# VIGILOS Official Mirrors
Server = https://repo.vigilglm.ai/$repo/$arch
Server = https://mirror1.vigilglm.ai/$repo/$arch
Server = https://mirror2.vigilglm.ai/$repo/$arch

# Geographic mirrors
Server = https://au.mirror.vigilglm.ai/$repo/$arch
Server = https://us.mirror.vigilglm.ai/$repo/$arch
Server = https://eu.mirror.vigilglm.ai/$repo/$arch
```

---

## Comparison

### Proposed VpM targets (not verified capabilities)

| Feature | VpM | pacman | DNF | apt |
|---------|-----|--------|-----|-----|
| Native Format | `.vpm` | `.pkg.tar.zst` | `.rpm` | `.deb` |
| RPM Support | Planned | ❌ | ✅ | ❌ |
| DEB Support | Not planned | ❌ | ❌ | ✅ |
| Parallel Downloads | Planned | ✅ | ✅ | ❌ |
| Delta Updates | Planned | ❌ | ✅ | ❌ |
| AUR-like Repo | Planned ViR | ✅ AUR | ❌ COPR | ❌ PPA |
| Written In | Rust | C | Python | C++ |
| Transaction Safety | Planned | ✅ | ✅ | ✅ |
---

## Development Status

### Current phase: design proposal; implementation unverified

| Component | Evidence in this checkout |
|-----------|---------------------------|
| Native format, library, CLI, solver, repository and build system | Planned; no implementation present |
| Documentation | Design proposal; not proof of working transactions |
| External VpM repository | Public URL returned HTTP 404; private implementation, if any, remains unverified |

### Roadmap

#### Phase 1: Foundation (unscheduled)
- [ ] Core library implementation
- [ ] Basic CLI commands (install, remove, query)
- [ ] Local package installation
- [ ] Package database

#### Phase 2: Repositories (unscheduled)
- [ ] Repository synchronization
- [ ] Dependency resolution
- [ ] Parallel downloads
- [ ] Mirror support

#### Phase 3: RPM ownership decision and compatibility (unscheduled)
- [ ] RPM parsing and installation
- [ ] Fedora repository support
- [ ] Mixed dependency resolution

#### Phase 4: Build System (unscheduled)
- [ ] VPMBUILD parser
- [ ] Package building
- [ ] ViR integration

---

## Contributing

We welcome contributions to VpM! See the main [VIGILOS README](README.md#contributing) for general contribution guidelines.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/vigilglm/vpm.git
cd vpm

# Install Rust (if not installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Build the project
cargo build

# Run tests
cargo test

# Run with debug output
RUST_LOG=debug cargo run -- install example
```

### Code Style

- Follow Rust standard formatting (`cargo fmt`)
- Use `clippy` for linting (`cargo clippy`)
- Write tests for new features
- Document public APIs

---

## License

VpM is distributed under the **GNU General Public License v3.0**.

---

<p align="center">
  <strong>VpM</strong> — Simple. Fast. Flexible.
</p>

<p align="center">
  Part of the <a href="README.md">VIGILOS</a> project
</p>
