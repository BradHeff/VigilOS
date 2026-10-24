# Dark theme validation — 24 October 2026

Both delivered editions completed the VM acceptance described here. Source-promotion and artifact-copy results are confirmed separately by `LATEST-PROMOTION.json` and `DELIVERY.json`; those receipts identify the final recovery backup and copied files.

The current project was snapshotted from `/home/bheffernan/Project/VigilOS` at `cc498d7d3c4e0fbc69d361f03a0e0e7b79c00035`. It includes the user's newer dark artwork; no older lab source snapshot was copied over that checkout. The maintained entry point remains `bash scripts/build-and-brand.sh`, building both editions by default. Host packages, shell/login/security settings and physical disks were not changed.

## Artifacts and build evidence

| Image | SHA256 | Bytes | Status |
| --- | --- | --- | --- |
| KDE | `00edf5246ef8b8ce0a930efd08adb8932d0f36693ccaf111665c0f4b9fdbd384` | 5288558592 | Accepted VM evidence below |
| Initial i3 | `f946f4652bd91b0091315e8815ad052a38b7e75774a0e7e8e7d005b0115795f1` | 5319884800 | Rejected: Qt application opened light |
| Corrected i3 | `00b4d2da578b36db1067b99a54e5f571ce47aeffae70a62630e15de245e9f0fd` | 5319950336 | Accepted after fresh installation and complete VM acceptance |

Initial both-edition fresh run `run-20261023T235544Z` finished at 00:24:43 UTC. Corrected i3 fresh run `run-20261024T012541Z` finished at 01:40:59 UTC. Signed official Fedora 44 live/cloud inputs were verified; all package operations, mounts and image assembly ran inside sequential 6 GiB/four-CPU disposable builders. Independent host transfer hashes, embedded media checks, BIOS/UEFI boot entries and a single EFI partition passed. Public build-evidence archives contain validation, branding, package-manifest and bootstrap logs; private keys and VM disks are excluded.

An earlier fresh build failed because a source validator mistakenly required a documentation file that is intentionally excluded from the builder source CD. Only that documentation assertion was removed; asset, syntax, contrast and host guards remained. The failed run was retained, then restarted from fresh input/overlay.

## Supplied artwork and changed surfaces

All four original user PNG exports and `PLASMA-CONFIGS/VIGILOS-SDDM/background.png` remain byte-for-byte unchanged. The user clarified that the already changed “KDE splash” meant this SDDM background. It was visually confirmed dark before editing and on actual installed SDDM boots.

The canonical 3840×2160 wallpaper SHA256 is `de5f2e826828bde96f19ea936ffc3caada822692e4ff5c86c0930645b29be2b0`; the preserved 1920×1080 SDDM source is `1c6aedd926a6e55b10023771faff28589e8de47d6f42bd9a87a56bf1b8658d0d`. `branding/wallpapers/dark-assets.json` records all supplied dimensions/hashes. Creation and upscale history are unknown; provided dimensions do not establish native production resolution. Earlier city art remains historical; its old active wallpaper choice was removed. The i3 import manifest is the earlier sanitized-import baseline, including its earlier wallpaper hash; it is not the current dark-build hash manifest.

Active surfaces use the faded dark VIGIL mark: desktop defaults, native SDDM and LightDM logins, lock screens, GRUB and a new separate Plasma splash derivative. The user's SDDM PNG is preserved, including in the fallback theme. Original splash source packages and third-party credits/licenses remain. KDE selects actual PurPurNight-Plasma, the VIGIL Dark palette, native Breeze decoration and shared dark GTK3 settings; GTK4 uses its native Default theme with a dark preference. i3 retains its portable Polybar/Rofi/Alacritty/GTK theme and excludes the NVIDIA-only bar module.

SDDM uses aspect fit with a neutral matte and source contrast checks of at least 4.5:1 for the tested text/control pairs. GRUB uses native padding. i3 wallpaper/lock use max/fit modes; Plasma desktop and GTK greeter use native aspect-preserving image handling. Actual resolution captures are needed to assess composition; this is not a full accessibility certification or a claim about all application content.

## KDE actual acceptance

A fresh native Anaconda UEFI installation on an owned 48 GiB disk completed. Normal Exit restored Enforcing. The disk booted without an ISO to dark SDDM; an uninterrupted password login reached the new dark splash and Plasma desktop. Native Dolphin and Brave chrome were visibly dark. Actual VIGILDark/PurPurNight/KSplash defaults and desktop-portal dark preference were verified.

The native lock used the new wallpaper, rejected an intentionally wrong test password and accepted the correct one. Signed `dnf upgrade --refresh` and native SDDM/Wayland-session/Brave reinstallation completed; product integrity/defaults survived. A graceful OS reboot and ordinary password login passed final checks at 00:46:30 UTC: Enforcing, installed cleanup/root locked, package integrity, no failed system/user units, no coredumps, no full-journal AVC denials or checked OOM findings.

Desktop captures were actually 1024×768, 1280×800, 1920×1080 and 3840×2160; lock captures 1280×800/4K. Native SDDM cold boots were inspected at 1024×768, 1280×800 and 4K, including normal greeter shutdown controls. A BIOS live boot reached the desktop and normal Konsole verified firmware absence at `/sys/firmware/efi`, Enforcing and kernel 7.2.11-200.fc44 at 00:51:36 UTC. This was a BIOS live smoke check, not a fresh BIOS installation.

KDE evidence is in `dark-kde-uefi`, `dark-kde-bios` and `KDE-ACCEPTANCE.json` beneath this task's evidence directory.

## i3 issue, correction and acceptance

The first i3 candidate completed a fresh UEFI installation and showed a dark native GTK greeter and GTK application. A normally launched Qt Dolphin window was visibly light, so that candidate was rejected for final acceptance. A Qt GTK3 bridge probe made it dark. That probe exposed a native portal dependency failure: the portal's unchanged `Requisite=graphical-session.target` could not be met by the original minimal i3 session.

The correction selects the existing GTK3 Qt platform theme in the i3 session, imports selected display/desktop/theme environment into the user activation manager, provides an i3 GTK portal preference and starts a native i3 user-session target bound to the graphical-session target. Stop propagation terminates graphical-only services when i3 ends. Existing native service guards, RefuseManualStart, PAM, SELinux and permissions were preserved. A prototype verified actual dark-mode Settings.Read, then clean inactive targets/portals after stop and successful restart at 01:21:41 UTC. An initial stop test without propagation failed and was retained before correction. This is ordinary desktop infrastructure, not SIERRA functionality.

Only i3 runtime/packaging paths changed after KDE acceptance; shared KDE code/assets and the validator stayed identical. The accepted KDE artifact remains valid. The corrected i3 desktop RPM is 1.2-4; it was rebuilt from fresh verified base input, not patched into an old ISO.

Corrected live acceptance passed at 01:45:38 UTC: normal Qt launch dark, actual GTK portal preference, active native session targets, required apps/helpers/integrity, Enforcing and no checked failed units/cores/AVCs. A new native fresh UEFI installation completed; normal Exit restored Enforcing and passed live checks at 01:52:45 UTC. ISO-free native LightDM password login reached the installed i3 desktop with live-only items removed. Qt Dolphin and GTK Thunar were visibly dark together. Alacritty loaded the cleaned Bash configuration and showed `<main>` in a disposable local Git fixture. Brave opened with dark chrome; normal encrypted keyring first-use setup completed with the nonblank test-account password. No credential-store bypass was used or shipped.

Signed native upgrades and LightDM/GTK/i3/i3lock/X-init/Brave reinstallation completed, followed by full defaults/integrity checks at 02:01:02 UTC. The native color lock rejected one wrong password (actual screen and PAM evidence), accepted the correct one and exited. Normal graphical Logout returned to LightDM; the i3 and graphical targets, both portals and idle locker were inactive, with no cores/AVCs, at 02:05:29 UTC. Ordinary password login restored the dark portal session and exactly one locker at 02:06:36 UTC. The normal graphical Reboot action then returned to LightDM. Uninterrupted password login and final full checks passed at 02:11:30 UTC: Enforcing, cleanup/root locked, package integrity, no failed system/user units, no coredumps, no full-journal AVC denials or checked OOM findings.

Actual native LightDM, desktop and lock captures were inspected at 1024×768, 1280×800 and 3840×2160 using cold boots at the selected mode. Native lock authentication and normal user poweroff worked at the additional resolutions. These check default startup composition, not an automatic i3 monitor hot-plug handler. A BIOS live desktop and normal Alacritty verified `I3_BIOS_LIVE_PASS`, Enforcing, kernel 7.2.11-200.fc44 and guest UTC 02:16:29. This is a BIOS live smoke check, not a fresh BIOS installation. All owned test VMs were powered off. Current i3 evidence is in `dark-i3-qt-fixed-uefi`, `dark-i3-qt-fixed-bios` and `I3-ACCEPTANCE.json`. The older rejected i3 candidate is retained separately and is not part of delivery.

Implementation references: [Qt theme selection](https://github.com/qt/qtbase/blob/dev/src/gui/kernel/qguiapplication.cpp), [desktop portal configuration](https://flatpak.github.io/xdg-desktop-portal/docs/portals.conf.html), [scoped activation environment](https://dbus.freedesktop.org/doc/dbus-update-activation-environment.1.html), [graphical-session lifetime](https://www.freedesktop.org/software/systemd/man/latest/systemd.special.html#graphical-session.target) and [native stop propagation](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html#PropagatesStopTo=). Actual guest behavior, not reference availability, establishes the tests above.

## Evidence, preservation and limits

Detailed evidence root: `/home/bheffernan/Documents/Codex/2026-10-22/task/dark-20261023/work/evidence`. The recovery backup of current public source and opaque entire Git is `work/backups/current-project-20261023T233857Z/source-and-git.tar`, SHA256 `542b793210b79571f14bd49970b460d3847f94776339e1f08d671cfb0381ea98`. A targeted promotion must make a fresh verified backup and preserve all newer user edits, original Git and the two protected legacy ISO files. Their contents are not accessed; preservation checks use lstat metadata in the same host namespace. The final `LATEST-PROMOTION.json` and `DELIVERY.json` receipts identify the fresh verified promotion backup and final artifact hashes; protected legacy ISO contents are excluded from all source archives and never read.

An initial staging mkdir at `/home/bheffernan/Project/VigilOS/dark-20261023` was blocked by the read-only sandbox; it is known not to have executed. Staging moved to the writable task root, without retrying that target. One old i3 test VM lost its execution session before a probe; the cause is unknown and the run was recorded interrupted, never counted as graceful reboot/poweroff. The prototype was subsequently shut down normally.

QA-only corrections are recorded in `QA-REPAIR.json`: preserve Plasma's real XDG defaults path in native queries; distinguish intentionally disabled live idle locking from required installed locking; account only for two SDDM runtime directory differences that exactly match the signed native tmpfiles configuration. No product permission/security workaround was used. Native virtual-display/TDX, multiple-file-manager provider and Anaconda teardown warnings were retained; successful installation/boot is established separately. The final i3 boot also retained a native gkr-pam daemon-control-file startup message. Normal encrypted keyring setup and browser operation were checked; no credential or PAM workaround was applied. Do not claim zero logged warnings.

Tests use isolated single-display VMs and dummy accounts. Hardware, proprietary GPUs, Secure Boot, physical multi-monitor setups, separate HiDPI scale factors and all future upstream package versions are not certified. This is a development candidate, not a publicly signed production release. The SIERRA integration plan is future development only; no SIERRA runtime, launcher or automation was implemented.

## Delivery and reproducible entry point

Verified artifacts and public acceptance evidence: `/home/bheffernan/Project/VigilOS/.build/output/dark-20261024T021922Z`. The `.iso.sha256` files verify the exact delivered images; build-evidence archives retain their package manifests. Final copy/pointer evidence is in `DELIVERY.json`. Previous validated outputs remain in place.

From the project directory run `bash scripts/build-and-brand.sh` to build both editions, or select `--desktop kde` / `--desktop i3`. The command applies these defaults and repairs and verifies inputs/media/transfer hashes. GUI acceptance is documented separately. Repository updates can change future output versions/hashes; the tests above certify this snapshot. See [BUILD.md](BUILD.md) and the future-only [SIERRA plan](SIERRA-INTEGRATION-PLAN.md).
