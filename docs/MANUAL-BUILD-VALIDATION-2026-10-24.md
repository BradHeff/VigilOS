# Manual clean-build verification — 24 October 2026

**Verification finished with defects. These original images boot and install, but are not fully accepted.** PackageKit repository refresh fails in both editions; i3's native LXPolKit authorization dialog is light; KDE's desktop wallpaper crops the mark at 1024×768. No product fix, rebuild or replacement image was made during this verification.

Verification completed: 24 Oct 2026 13:43:10 UTC / 25 Oct 2026 00:13:10 ACDT. Dates below include UTC and Australia/Adelaide (ACDT, UTC+10:30). This report concerns the user's manual `bash scripts/build-and-brand.sh` run after deleting `.build`, rather than the earlier dark-theme candidates.

## Exact original artifacts

Output directory: `/home/bheffernan/Project/VigilOS/.build/output/20261024T062157Z/`.

| File | Bytes | Original modification time, UTC | Adelaide |
| --- | ---: | --- | --- |
| `VIGILOS-1.2-kde-x86_64.iso` | 5,288,624,128 | 24 Oct 2026 06:36:04.539063 | 24 Oct 17:06:04.539063 ACDT |
| `VIGILOS-1.2-i3-x86_64.iso` | 5,319,950,336 | 24 Oct 2026 06:50:34.126608 | 24 Oct 17:20:34.126608 ACDT |

Original SHA256 values, independently recorded before the first VM test:

```text
5dbf63472d06a6469f48822b8aa9b3fcca2e47011429a040edc7c0d6ca5ef3c8  VIGILOS-1.2-kde-x86_64.iso
7bec89ac12dc8afacdf5ae3823a05d165c5d237344f1242f851e0ae333b288e4  VIGILOS-1.2-i3-x86_64.iso
```

Both agree with the build's transfer manifests and published `.iso.sha256` files. Independent final SHA256 verification after all guest tests also passed. Original inode, size, mode, modification/change timestamps and `.build/LATEST.json` were preserved. That pointer's `complete: true` describes build completion, not acceptance.

The matching public build-evidence archives were independently checked and extracted into this verification's evidence directory. They contain package manifests, bootstrap, validation and branding logs. No private builder credentials were inspected or copied.

## Clean-build and media evidence

The recreated cache inputs match the pinned official Fedora 44 KDE and Cloud image hashes. Independent `gpgv` checks confirmed fingerprint `36F612DCF27F7D1A48A835E4DBFCF71C6D9F90A6`. Cache timestamps follow this build's start. Both separate 104 GiB builder overlays reference the current official Cloud base; the build logs show dependency bootstrap, and all 25 scripts extracted from each standalone source CD match the current project. No active build script depends on the old lab path. The current source/prerequisite `--check` passed without rebuilding.

These files support the clean-build provenance. The user's deletion of the previous `.build` is trusted history; present files alone cannot independently prove a past deletion. No previous ISO, VM disk or acceptance result was reused. Reused QA tools were copied into this new verification workspace and corrected where necessary.

Both original images passed independent embedded-media checks and ISO boot-layout inspection, including BIOS/UEFI entries and EFI partition structure. Both then actually booted in each firmware mode.

## Actual acceptance results

Each edition used its own new 48 GiB disposable disk, 6 GiB RAM and four CPUs. Guests ran sequentially, without host shares. Fresh installations used the normal graphical installer, a new ordinary administrator and a locked root account. Installed tests booted with the ISO removed. Test VMs were shut down normally afterwards.

| Check | KDE | i3 |
| --- | --- | --- |
| SHA256, embedded-media check, BIOS/UEFI ISO structure | PASS | PASS |
| Actual UEFI live desktop and fresh graphical UEFI installation | PASS | PASS |
| Normal installer exit, restored Enforcing, temporary profile cleanup | PASS | PASS |
| Installed media-free greeter/password login | PASS: SDDM | PASS: LightDM |
| Native logout, ordinary relogin, GUI reboot and changed boot ID | PASS | PASS |
| Further cold installed boots at 1024×768 and 3840×2160 | PASS | PASS |
| Wrong lock password rejected; correct password unlocks | PASS | PASS |
| Dark desktop, Qt and GTK3 defaults; normal dark Brave chrome | PASS | PASS |
| Dark native GTK2 LXPolKit dialog | N/A | **FAIL**; authentication itself passes |
| Dark greeter, lock and boot branding; KDE Plasma splash | PASS | PASS; Plasma splash N/A |
| Image proportions and controls at 1280×800, 1024×768, 3840×2160 | PASS, with desktop crop below | PASS |
| Full wallpaper mark on the 1024×768 desktop | **FAIL: left edge cropped** | PASS |
| Signed native DNF refresh/upgrade and essential package reinstall | PASS | PASS |
| PackageKit native repository refresh | **FAIL: exit 7, HTTP 404** | **FAIL: exit 7, HTTP 404** |
| Brave HTTP, HTTPS and HTML defaults after updates/reboot | PASS | PASS |
| Required i3 helpers, clipboard, Git prompt and session lifecycle | N/A | PASS |
| Post-reboot root lock, installed cleanup, product/Bash integrity | PASS | PASS |
| Post-reboot Enforcing, current units, coredumps, full-journal AVC/OOM checks | PASS | PASS |
| Actual BIOS live desktop, branded GRUB/Plymouth and Enforcing | PASS | PASS |
| BIOS installation; physical hardware; Secure Boot | NOT RUN | NOT RUN |

The final comprehensive installed health checks completed at **24 Oct 11:51:06 UTC / 22:21:06 ACDT** for KDE and **24 Oct 13:21:58 UTC / 23:51:58 ACDT** for i3. Cold display checks followed those checks. BIOS live terminal evidence shows kernel `7.2.11-200.fc44.x86_64`, absence of EFI firmware and Enforcing; the i3 capture is timestamped **24 Oct 13:38:40 UTC / 25 Oct 00:08:40 ACDT**. BIOS live coverage does not certify BIOS installation.

In i3, exactly one each of Polybar, LXPolKit, Greenclip and xss-lock accompanied i3. They stopped on native logout and returned once on relogin. Native GTK portal and graphical-session targets followed the session lifecycle. Alacritty showed the Git `<main>` prompt, Node 24.18.0, npm 11.16.0, Python 3.14.8 and Flatpak 1.18.4. A known clipboard fixture round-tripped through xclip and appeared in Greenclip/Rofi. Native LXPolKit successfully authorized the harmless `/usr/bin/true` command. Brave used its normal encrypted-keyring prompt with a nonblank test password. Normal Chromium sandbox/credential defaults were retained.

## Defects and proposed corrections

1. **PackageKit refresh fails in both original installations.** Actual `pkcon refresh force` exits 7, requesting `https://mirrors.fedoraproject.org/metalink?repo=updates-released-f1.2&arch=x86_64`, which returns 404. KDE Discover visibly reports “Update Issue.” Native signed DNF refresh/upgrade works with `/etc/dnf/vars/releasever=44`. PackageKit 1.4.0's dnf5 backend explicitly resets releasever from the OS version after libdnf setup, consistent with the observed product-version mismatch. See the [versioned upstream implementation](https://github.com/PackageKit/PackageKit/blob/v1.4.0/backends/dnf5/dnf5-backend-utils.cpp#L128-L140). Propose base-release compatibility that covers both DNF and PackageKit while retaining VIGIL 1.2 identity, signed Fedora 44 repositories and TLS/GPG verification. An RPM capability or DNF variable alone must not be assumed sufficient. Select and test the repository/backend approach before rebuilding separate candidates.
2. **i3 LXPolKit is light.** The actual native authorization prompt uses GTK2. The supplied dark GTK2 theme exists, but the tested user/system GTK2 settings are absent and the theme's Murrine engine is missing. GTK3 and Qt applications are dark. Propose explicit GTK2 defaults plus a compatible engine or tested compatible dark GTK2 theme, retaining normal LXPolKit/PAM/polkit authentication.
3. **KDE 4:3 desktop composition crops the mark.** At 1024×768 the native fill mode clips its left edge; proportions remain correct. SDDM and lock preserve the full mark. Propose aspect-fit with a matching matte on narrow displays, preserving the user's artwork.

A nonblocking packaging observation: `scripts/lib/remix.sh` overwrites native SDDM's global `.face.icon`. Signed SDDM reinstallation restores that native file, while the theme-owned VIGIL avatar remains intact and actual SDDM stays branded after logout/reboot. Prefer the existing theme-owned asset and remove the redundant native-file overwrite in a future change. The remaining SDDM RPM directory metadata differences match native tmpfiles rules; they are not corrupted native files.

These are proposals only. The original manual build remains the tested artifact with these failures recorded. No security weakening, product source repair or replacement build was used to obtain passes.

## Evidence and reproduction

Evidence root: `/home/bheffernan/Documents/Codex/2026-10-22/task/manual-20261024/work/evidence/`.

- Inventory and provenance: `ORIGINAL-MANUAL-ARTIFACTS.json`, `CLEAN-BUILD-PROVENANCE.json`, `MEDIA-CHECK-RECEIPT.json`, `kde-media/`, `i3-media/`, `kde-manual-build/`, `i3-manual-build/`.
- Fresh installer completion: `kde-install-final.png`, `i3-install-success.png`. Final installed logs: `kde-final-post-reboot-check.log`, `i3-final-post-reboot-check.log`; changed boot IDs and absent media: `KDE-REBOOT-PROOF.json`, `I3-REBOOT-PROOF.json`.
- Native update results: `kde-native-update-start.log`, `i3-native-update-progress.log`. Actual failures: `kde-packagekit-refresh-result.log`, `i3-packagekit-refresh-result.log`, `kde-discover-current.png`, `i3-lxpolkit-auth-prompt.png`; functional polkit result: `i3-lxpolkit-authorized-true.png`.
- Display evidence: `{kde,i3}-{1024x768,3840x2160}-visuals/` contains native-resolution greeter, desktop, lock and unlocked captures. `kde-installed-plasma-splash.png`, `{kde,i3}-installed-plymouth.png`, `i3-bios-boot/early-frames/012.png`, `kde-bios-early/early-frames/012.png` show actual branding. `{kde,i3}-bios-firmware-kernel-enforcing.png` show the BIOS live checks.
- `KDE-VERIFICATION-RESULT.json`, `I3-VERIFICATION-RESULT.json`, `OBSERVATIONS.json`, `HARNESS-NOTES.md`, `PRESERVATION-BEFORE-DOCS.json`, `PRESERVATION-AFTER-DOCS.json` record results, exceptions and preservation.

To repeat the original artifact checksum check:

```bash
cd /home/bheffernan/Project/VigilOS/.build/output/20261024T062157Z
sha256sum -c VIGILOS-1.2-kde-x86_64.iso.sha256 VIGILOS-1.2-i3-x86_64.iso.sha256
```

For a fresh disposable test, use the maintained launcher as an ordinary host user, selecting a **new private test root** for each edition:

```bash
cd /home/bheffernan/Project/VigilOS
export VIGIL_EXECUTION_APPROVED=1 VIGIL_ALLOW_NETWORK=1
export VIGIL_TEST_ROOT=/path/to/new-private-kde-test
export VIGIL_FIRMWARE=uefi VIGIL_DISPLAY_MODE=1280x800
bash scripts/test-vm.sh live vigil "$PWD/.build/output/20261024T062157Z/VIGILOS-1.2-kde-x86_64.iso"
# Complete the normal installer and shut down; then boot the same disk without media:
bash scripts/test-vm.sh installed vigil
```

Repeat with the i3 ISO and a different new test root. Keep only one resource-heavy guest active, at most 6 GiB total VM RAM. Use `VIGIL_FIRMWARE=bios` for a separate live boot check. The QA tools and reviewed guest probes used here are retained in the same task's `work/tools/` and `work/evidence/`; no host package or security changes are needed by this verification.

## Limits, warnings and preservation

Default pixel scaling was inspected at three resolutions, not independent HiDPI scale factors or physical multi-monitor configurations. No physical GPU, proprietary drivers, Secure Boot or hardware qualification is claimed. LibreOffice and other required packages were verified present; this is not exhaustive functional certification of every bundled app or input method. Virtual hardware, portal/app-ID and transient imsettings warnings are retained in logs. Successful final unit/coredump/AVC/OOM checks do not mean zero journal warnings or negate the failed PackageKit feature. Its intentionally failed QA service was preserved until an ordinary reboot, rather than reset to hide the result.

Harness corrections included the native KWin package name, installed KDE's graphical VT, native lock shortcuts and test timing around Anaconda's temporary permissive phase. Original unsuccessful QA attempts were retained. One cleanup probe, `find /run/user/1000 -maxdepth 1 -name 'vigilos-installer-brave.*' -print`, received **Permission denied** for `/run/user/1000/doc`. That metadata lookup was blocked; no portal contents were inspected and the target was not retried. A narrow check of only generated installer-profile paths passed independently. No requested validation remains blocked by that denial. Full details are in `HARNESS-NOTES.md`.

Final preservation checks independently rehashed both original ISOs and compared product source, original `.git` data/metadata/xattrs and the two protected legacy ISO metadata records. Protected contents were never read. Product source and Git were preserved; the only project writes are this report and its README/build-guide documentation links. No host settings, host login/security configuration, commits, pushes or publication were changed. All owned validation VMs are off.
