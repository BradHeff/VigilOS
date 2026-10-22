# VIGIL OS development validation — 21–22 October 2026

Status: **candidate033 actual BIOS/UEFI installations, ISO-free first boots and repeated boots passed. The final retained UEFI VM was restored from its validated checkpoint and cold-booted successfully; source promotion is verified by its separate scoped record.** This record distinguishes actual runs from historical claims. It does not certify a publicly signed production release.

## Exact artifact and provenance

- Product: VIGIL OS1.2 “Loopback”, Fedora44 base, KDE Plasma Wayland/SDDM.
- ISO: `/home/bheffernan/Documents/Codex/2026-10-21/task-3/vigil-lab/output/VIGILOS-1.2-candidate-033.iso`.
- Bytes:5,250,678,784. SHA256: `90693f5cd9b85e56bab6c889022bae28d8009bea3f7a162a6ea02592be2e1102`.
- EROFS payload:4,882,137,088 bytes; SHA256 `67f01719cb9177683ff2a79e874d8a7584caa9c8b72894b864ba3ce74e939701`.
- Product branding RPM:1.2-16.fc44; wallpaper compatibility RPM:1.2-1.fc44.
- Kernel7.2.11-200.fc44, Plasma6.7.5, Frameworks6.31.0, Qt6.11.2; virtio display/llvmpipe in the test VM.

The official Fedora44 KDE input and repository/key checks are retained in the private lab. Candidate033 was made by incrementally updating a marked prepared root, building/installing product RPMs through normal DNF transactions, checking native/product integrity, encoding target SELinux labels into EROFS and assembling a fresh hybrid ISO. Matching kernel/initramfs from candidate027 were reused: their kernel and Plymouth payload did not change in the later appearance/asset fixes. A clean from-scratch execution of the final complete source route was not repeated. The exact source snapshot and code/asset hashes are in `evidence/candidate-033-source-code-manifest.json`.

These local product RPMs are **unsigned development artifacts**. Fedora/Brave repository package verification and TLS checks stay enabled. No private signing key, public repository, commit, push or release publication was created.

## Actual acceptance evidence

Evidence paths below are relative to the private lab `evidence/`.

| Check | Actual result | Evidence |
| --- | --- | --- |
| Media and boot structure | Full transfer SHA, media MD5, BIOS+UEFI entries and single appended EFI partition passed | `candidate-033-verification/` |
| UEFI installation | Actual4GiB guided whole-disk graphical Anaconda installation succeeded; Btrfs root/home, ext4 boot, EFI partition | `vigil-033-uefi/13-install-state.png` |
| BIOS installation | Actual final0334GiB guided whole-disk graphical install succeeded; BIOS boot partition, ext4 boot and Btrfs; ISO-free first boot and warm reboot with normal graphical password login passed | `vigil-033-bios/11-install-result.png` |
| Live desktop | Exactly one Install VIGIL OS shortcut; correct launcher/wallpaper/panel, no default Fedora shortcut recreation observed | Both033 live captures |
| Installer | Official native Brave app viewer; correct VIGIL header and product favicon/window/task icon; actual1024×768 layout fits | `vigil-033-uefi/04-installer-1024x768.png` |
| ISO-free installed boot | Automatic7.2.11 selection, branded SDDM and normal password login, no repeated Plasma Setup | `vigil-033-uefi/installed-firstboot/`, `first-login/`; `vigil-033-bios/firstboot-state.log`, `warm-login-state.log` |
| Installed cleanup/security | Root locked, liveuser absent, no installer shortcut, Enforcing; no native installer/port80 listener on installed boot | `vigil-033-uefi/firstboot-state.log` |
| Required applications | Actual command execution/default handlers and GUI tests below passed | `required-apps-and-cleanup.log`, GUI captures |
| Branding settings | Correct About System logo/name, one VIGIL City gallery tile and VIGIL theme names after native package reinstalls | `27-about-system.png`, `33-gallery-city.png`, `35-global-themes-ready.png` |
| Lock and authentication | Normal graphical password login, normal sudo password challenge and normal lock-screen password unlock passed | Login/auth/lock captures |
| Updates | DNF history29 and30 StatusOk; signed upgrade plus12 native logo/desktop/boot package reinstalls; dependency and product/native RPM checks clean | `update-history-and-qml.log`, `update-persistence.log` |
| Repeated UEFI boots | Two actual warm reboots and native720p/1440p cold boots with normal logins passed; Enforcing, no fresh installed-boot AVC/coredump/failed system or user units | `warm1-state.log`, `warm2-state.log`, `native-*-state.log` |
| Pixel/scaling matrix | ActualPNG dimensions asserted:1024×768,1280×720,1280×800,1920×1080,1920×1200,2560×1440 and3840×2160 at200% | `layouts/`, separate native cold-boot captures |

BIOS firstboot and warm login also verified all required package versions/three Brave MIME handlers, liveuser/installer/autologin cleanup, locked root, Enforcing, no fresh-boot AVCs/coredumps/failed system or user units. BIOS native RPM verification reported two mode-only differences: `/boot/grub2` is0755 (RPM expects0700), and the unused BIOS-install `/boot/efi/EFI/fedora/BOOTX64.CSV` ghost file is0600 (RPM expects0700). Content/package ownership was not altered to hide these installer-mode differences. Product RPM verification and DNF dependency checks passed. Exact details: `vigil-033-bios/integrity-mode-detail.log`.

The initial1280×800 virtual EDID does not advertise720p/1440p. The helper records those as unavailable rather than treating an unchanged framebuffer as success; separate cold boots changed the virtual monitor and asserted both greeter and desktop pixels.

## Applications shipped and exercised

| Software | Version observed | Test |
| --- | --- | --- |
| Brave |1.97.59; keyring1.19 | Actual HTTPS browser window through xdg-open; HTTP/HTTPS/HTML defaults resolve brave-browser.desktop |
| LibreOffice |26.2.6.3 Writer/Calc/Impress packages | Writer GUI loaded a real ODT; headless ODT→PDF produced a valid15,168-byte PDF; full Calc/Impress workflows were not tested |
| Node.js/npm |24.18.0 /11.16.0 | Actual command execution, native node/npm commands; Fedora uses versioned nodejs24/bin/npm-bin providers |
| Python3 |3.14.8 | Actual SSL/SQLite imports; OpenSSL3.5.9 and SQLite3.51.2 observed |
| Flatpak |1.18.4 | Actual executable/version; no third-party Flatpak application installation claimed |

Firefox, fedora-bookmarks and the optional Fedora Media Writer application are absent. Anaconda remains available. No automatic RPMFusion/proprietary NVIDIA/Flathub application install ran. The ordinary signed Fedora update installed OpenH264 from the standard configured Fedora codec repository, replacing noopenh264; this is distinct from adding RPMFusion.

## Measured fixes and appearance

Unbounded installer compression on020 killed Plasma. The final4GiB UEFI install kept the same live PlasmaPID2387, had no kernel OOM, minimum MemAvailable1169.5MiB, and observed `zstd -3 -q -T1` at54.1MiB maximum RSS. The final BIOS4GiB installation also kept the same PlasmaPID2397 with no OOM, minimum MemAvailable1190.1MiB and maximum compressorRSS54.1MiB. The sampler includes the pre-install interval and reports logical swap use, not physical compressed-zram memory.

Anaconda itself temporarily uses Permissive during live installation and restores the saved Enforcing mode on normal Exit. Installed startup remains Enforcing; no product policy bypass was introduced.

The optional Git prompt file/function is guarded; actual clean Konsole startup has no missing-file/function errors. The Brave installer viewer owns a fresh temporary profile, avoids a live KWallet wizard, supervises the native executable and removes its profile on normal Exit. Installed personal browser settings and Chromium sandboxing are retained.

The old raster mark was replaced with renders of the existing four vector shield/V paths and original colors; display text is VIGIL OS. Wallpaper is native **1672×941**. Larger display sizes are upscales, not native4K. GRUB/background/QML fit preserves aspect; actual multi-aspect captures were reviewed. Plymouth retains the upstream149×43 canvas footprint; generated visible mark bounds139×35 were recorded. Actual boot captures show VIGIL menus/wordmark/greeter without square stretching.

Product assets/defaults use separate owned paths and supported user/XDG configuration. Native Fedora logo/core desktop files were restored and pass RPM verification. A thin product wallpaper RPM provides the unversioned f44-backgrounds-kde dependency contract while retaining original base-art attribution/licenses; it does not remove Plasma/SDDM. Upstream repo names, keys, package build suffixes, licenses, compatibility IDs and the signed `EFI/fedora` path intentionally retain provenance. Actual firmware entry label is **VIGIL OS**.

## Preserved issues and limits

- An unmodified Fedora plasma-drkonqi6.7.5 startup pickup job timed out after30minutes in an idle preflight with no actual crash. Native RPM verification, an empty-UID probe and matching upstream source support an upstream classification; a full30-minute stock Fedora service comparison was not run. Crash reporting is enabled and unchanged.
- One live UEFI diagnostic invoked kscreen-doctor without display environment and produced a514KiB Qt abort. The dump/evidence is preserved. Correct guarded Wayland invocation passed; live Plasma/installer survived. No such dump or AVC appeared on the fresh installed boots. This is not a globally zero-crash claim.
- After normal live installer Exit, the custom viewer/profile disappeared and Enforcing returned, but native Cockpit helper/bridge and127.0.0.1:80 listener remained until guest shutdown. Exact stock-live cleanup comparison is unrun. They were absent on the installed system; no kill/mask workaround was added.
- Native systemd scriptlet transient-service transport warnings occurred during reinstalls and also in the Fedora baseline. Actual unit exit/history/dependency/integrity and reboot results establish success. KWin output-configuration warnings after diagnostic VT changes also occurred on the baseline. No speculative Qt/driver fork or policy exception was introduced.
- Some optional global-theme preset preview references are generic and not separately validated captures of every palette. Current factory desktop, About, gallery, actual login/splash/lock and corrected SDDM preview were checked.
- Hardware, proprietary GPUs, inherited nouveau policy, suspend, Secure Boot and broad storage/encryption variants are untested. No host OS/packages/services/security/KVM permissions/firewall/firmware changes, physical disks, USB writes, host shares or credentials were used.

Normal tests used one4-vCPU VM at6GiB; installation stress used4GiB. Builder104GiB, VIGIL48GiB and baseline40GiB sparse virtual capacities sum to192GiB. Offline internal checkpoints preserve UEFI/BIOS states inside the same48GiB image rather than adding virtual disks. Old completed outputs were retained; byte-identical extent sharing preserved content/modes/ownership/mtime/xattrs. Allocation/ctime intentionally changed.

Boot samples are not desktop-ready or universal performance benchmarks. UEFI warm userspace graphical-target samples were2.173s and2.128s; one idle memory sample was1601MiB. The official Fedora KDE baseline was actually installed/updated to the same kernel/Plasma and compared at matching modes/resources, but cache/session history and a Mesa point-version difference prevent a strict speed claim. Both use software desktop rendering.

VpM remains a native `.vpm` design/roadmap: no Rust engine or production transactions are implemented here. RPM/DNF5/rpmdb remain the supported update path. Native package ownership/migration, signing/catalog, disposable-root prototype and genuine rollback require further work. AI-generated recipes remain untrusted; SQLite atomicity is not OS rollback.

Final retained VM: the validated UEFI checkpoint was restored and cold-booted ISO-free at1280×800. Normal password login and sudo authentication passed; a read-only serial check proved persistent lab fixture absence, locked root, Enforcing, native/product RPM integrity, DNF dependency consistency, VIGIL EFI entry and installed cleanup. Dolphin opened normally. Discover rendered its cached catalog and correctly reported offline because NAT was intentionally disabled in this final run; online package-UI transactions were not tested here (the real signed DNF transactions above were). No fresh-boot AVCs/coredumps/failed system or user units appeared. All owned VMs were then cleanly powered off.

## Source and recovery

The authorized original source destination is `/home/bheffernan/Project/VigilOS`. Promotion is verified separately in `evidence/LATEST-PROMOTION.json`: recoverable scoped archive before overwrite, source hash/metadata parity and complete original .git/HEAD/index preservation. Two unreadable legacy ISO files are excluded/protected from all backup/sync/delete operations and never content-read: `7fc9a279-0635-4ac7-ae28-f0bbb95207d1-live-installer.iso` and `a86cfb57-cfae-45a3-af6b-13ed09ab847d-live-installer.iso`. This is a source promotion with explicit exceptions, not a full-folder mirror/backup. VM disks, downloads, ISOs, test evidence and private history remain outside the promoted source.

Primary implementation references: [KInfoCenter per-user configuration](https://develop.kde.org/docs/administration/kinfocenter/), [Plasma scripting](https://develop.kde.org/docs/plasma/scripting/), [KDE wallpaper package enumeration](https://raw.githubusercontent.com/KDE/plasma-workspace/Plasma/6.7/wallpapers/image/plugin/finder/packagefinder.cpp), [Drkonqi pickup source](https://raw.githubusercontent.com/KDE/drkonqi/Plasma/6.7/src/coredump/processor/main.cpp), [watcher source](https://raw.githubusercontent.com/KDE/drkonqi/Plasma/6.7/src/coredump/coredumpwatcher.cpp).
