# Current build workflow

The user now requests a complete one-command fresh build of both KDE and i3 editions. See [BUILD.md](BUILD.md). New runs use fresh cloud overlays in the selected private workspace; earlier lab disks/checkpoints/ISOs are preserved. At most one builder/test VM is active for this task. Host packages/security/services remain unchanged. The historical candidate033 resource layout and test evidence below describe the earlier completed task, not limits or acceptance claims for the new implementation.

---

# VIGIL OS isolated build and acceptance plan

Status: execution was explicitly approved. Actual BIOS and UEFI installations, first boots, signed package updates and visual comparisons have run. Candidate033 BIOS/UEFI installation, firstboot and repeated-boot acceptance passed; the retained UEFI checkpoint was restored and cold-booted again, and final source promotion is verified in its separate scoped record; see `VALIDATION-2026-10-21.md` and the private lab `evidence/ACCEPTANCE.json`. Source promotion into the original project was later explicitly authorized and performed under a verified scoped backup, preserving `.git` and two protected unreadable legacy ISOs. Historical documentation is not new test evidence.

## Resource and storage boundary

Use /home/bheffernan/Documents/Codex/2026-10-21/task-3/vigil-lab only.
source/ is an effective-working-tree copy without .git, ISOs, or .vigil chat history.
vm/builder.qcow2: 104 GiB sparse capacity, 6 GiB RAM, four vCPUs.
vm/vigil.qcow2:48 GiB; vm/baseline.qcow2:40 GiB. Normal matched tests use6 GiB RAM and four vCPUs; the explicit low-memory stress test uses4 GiB.
The launcher serializes VMs, limiting active RAM to 6 GiB and aggregate disk capacity
of its three disks to 192 GiB. VNC/QMP/serial use private Unix sockets. The builder artifact forward is restricted to host loopback (127.0.0.1:18080); the guest server exposes only /build/export.
No host shares, physical disks, host USB, credentials, GPU passthrough, or daemon API.
Optional user-mode NAT is enabled only with VIGIL_ALLOW_NETWORK=1; no incoming port forward is used for target test VMs.
No host SELinux, firewall, kernel, KVM permissions, services, or packages are changed.

## Execution sequence after explicit approval

1. Review diffs, run scripts/validate.sh and required syntax/kickstart checks.
2. Download official Fedora 44 media and signed CHECKSUM/key data. Verify the key
   fingerprint against Fedora, checksum signature and image checksum; retain evidence.
   Do not weaken package signatures or import keys into the host user's keyring.
3. Launch the blank builder VM with approved official Fedora media. Install only on
   builder.qcow2. Prepare guest-local /build, a /etc/vigilos-disposable-builder marker,
   and official build dependencies. The actual route uses a verified official KDE live ISO;
   no osbuild-composer daemon is needed.
4. Transfer sanitized source on a read-only source ISO, then copy it to /build/source.
   With VIGIL_BUILD_GUEST=1, run /build/source/scripts/build-and-brand.sh there.
   It creates a new /build/output/candidate.* directory; no previous outputs are deleted.
   Build tools mount/chroot only within the disposable builder, never the host.
5. Transfer the resulting candidate ISO as a bounded artifact; no host filesystem share.
   Preserve compose/branding logs, manifest, checksum, package versions and ISO metadata.
6. Use scripts/test-vm.sh live vigil <candidate.iso>, then installed vigil after installer
   shutdown. Set VIGIL_EXECUTION_APPROVED=1 only after actual authorization.
   Run baseline with matching official Fedora KDE media, resources and display settings.
   VIGIL_FIRMWARE=bios selects a separate BIOS cycle; default is plain OVMF UEFI.
   Reinstall only the owned disposable guest disk; preserve earlier evidence directories.

## Acceptance matrix

| Area | Required observations and evidence | Current status |
| --- | --- | --- |
| ISO/media | SHA256, ISO MD5 media check, volume IDs, BIOS/UEFI boot entries | See final validation record / evidence |
| UEFI | Boot live media, visible GRUB labels/theme, basic graphics fallback | See final validation record / evidence |
| BIOS | Separate install cycle on disposable disk; media and installed boot | See final validation record / evidence |
| Installer | Launch actual Anaconda from desktop; complete storage, accounts, payload, bootloader; save logs | See final validation record / evidence |
| First boot | ISO removed, SDDM and Plasma reachable; liveuser absent, no NOPASSWD live rule, no installer shortcuts | See final validation record / evidence |
| Reboots | Two warm reboots plus shutdown/cold boot; identity, boot entries, watermark, login remain correct | See final validation record / evidence |
| Branding | GRUB, initrd/Plymouth, installer chrome/help/title, SDDM, Plasma splash, launcher, wallpaper, lock screen, settings About, console, terminal, shutdown/reboot | See final validation record / evidence |
| Layout | Same 1024x768 (4:3), 1280x720 and 1920x1080 (16:9), 2560x1440, and 1920x1200 (16:10); 100% and 200% scaling when supported | See final validation record / evidence |
| Image geometry | Compare Fedora/VIGIL visible logo bounds, aspect ratios, centering/cropping and padding at identical modes; no forced stretching | See final validation record / evidence |
| Services | systemctl --failed, journal warnings/errors, session/QML errors, portal/installer/display service logs | See final validation record / evidence |
| Startup | systemd-analyze time/blame/critical-chain; identify boot-critical work, repeat measurements after changes | See final validation record / evidence |
| Desktop | Launcher, file manager, terminal, settings, suspend availability, networking and package UI | See final validation record / evidence |
| Updates | DNF5 signed repository access; RPM database consistency; branding persists after relevant package update | See final validation record / evidence |
| SELinux | Measure AVCs, fix labels/ownership in guest; test enforcing in a disposable snapshot/cycle before claiming support | See final validation record / evidence |
| Comparison | Sequential identical Fedora KDE and VIGIL resource/display runs, cold and repeat measurements | See final validation record / evidence |

Final comparisons use already-available KVM, without host permission/security changes. The initial restricted tool view hid /dev/kvm; read-only escalated inspection confirmed it was already usable. Virtio display without host GPU passthrough uses software desktop rendering. These results do not prove native GPU snappiness, Secure Boot, broad hardware support or production readiness. TCG was used only for earlier builder setup attempts. Do not treat documented historical test claims as new results.

## First-pass feature differences

Official Fedora repositories plus the explicitly requested official signed Brave repository. Automatic RPMFusion, proprietary NVIDIA drivers and third-party Flatpak application installs are disabled. Normal configured Fedora codec updates remain supported. A user-visible opt-in
and separate signing/driver build tests are required before enabling these features.
The existing nouveau blacklist remains unchanged pending real hardware evidence.
The current candidate keeps SELinux enforcing and labels files during the build. It removes the old first-boot permissive rewrite, forced relabel, repeated initramfs rebuild and EFI stub overwrite. Candidate033 actual UEFI firstboot/repeated boots and signed update/reinstall checks retained Enforcing; exact current BIOS/final results are in the validation record.

## Remaining release engineering

The pipeline now builds local development vigilos-release-identity and vigilos-branding RPMs. Declare Provides/Conflicts/Obsoletes deliberately; preserve Fedora
repo keys, releasever=44, upstream licenses and signed EFI/fedora shim paths. Actual033 signed desktop/logo/boot package reinstalls, integrity checks and repeated UEFI boots proved the tested persistence path. Future public release work still includes clean from-scratch CI, independent theme packaging/signing and hardware acceptance. Anaconda WebUI uses product Cockpit branding and favicon; the inherited Fedora profile remains necessary for bootloader/storage compatibility.
VpM is a design document in this checkout; do not claim native transactions are built.
Retain RPM/DNF5 compatibility unless the user approves a separate native-package design.

## Static asset integration checkpoint

Parent-supplied relettered wallpaper was materialized through Library, matched SHA256
58f1ea66fc85ad7fa71358fb6e20ee78587600985bae92319b08d7bd078218ca,
and was visually inspected before integration. Native size is 1672×941, not 4K.
Canonical source/provenance: branding/wallpapers/source/. KDE package image:
branding/wallpapers/VIGILOS/contents/images/1672x941.png. Old Arxis imagery and
raster logos are preserved outside the packaging tree in evidence/baseline-assets/.

Clean logo SVGs reuse the existing four shield/V paths and blue/red/gold colors.
The spaced VIGIL OS wordmark source uses DejaVu Sans Bold text. Raster rendering was verified in the guest; outline-only/reproducible font-source work remains a public-release task. Guest-rendered derivatives were visually inspected; PNG bounds were measured and retained in evidence/generated-brand-dimensions.json. prepare-brand-assets.sh runs only within a
marked, disposable guest build work directory; it generates transparent, aspect-fit
raster derivatives and a 149×43 wordmark watermark. Rendering ran in the disposable guest. Actual033 boot/display captures and asserted pixel modes were compared with the Fedora baseline; exact limits are in the validation record.

VpM documentation now labels the local implementation evidence accurately, rejects
optional Fedora RPM signatures and SQLite-only RPM ownership, and leaves the native
system-ownership decision explicitly open. No manager implementation was added.
