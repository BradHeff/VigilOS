# Repaired clean-build validation — 24 October 2026

**The three reported defects are repaired in maintained source, and both separate rebuilt images passed the scoped VM acceptance below.** This report certifies the exact repaired images listed here. The user's original manual images remain unchanged and retain their failures in [the original report](MANUAL-BUILD-VALIDATION-2026-10-24.md).

Completed: 2026-10-24 20:32:00 UTC / 2026-10-25 07:02:00 ACDT. This remains a development candidate with local product RPMs; no public release signing or publication was performed.

## Exact repaired artifacts

Directory: `/home/bheffernan/Project/VigilOS/.build/output/repair-20261024T182322Z/`.

| File | Bytes | Original output modification time, UTC |
| --- | ---: | --- |
| `VIGILOS-1.2-kde-x86_64.iso` | 5288558592 | 2026-10-24T18:37:34.251326+00:00 |
| `VIGILOS-1.2-i3-x86_64.iso` | 5320212480 | 2026-10-24T18:52:56.042375+00:00 |

SHA256:

```text
b84cfbde3d42ccd720628827dc6e53fb93086afbe388bf6484cbc5d02ce59e00  VIGILOS-1.2-kde-x86_64.iso
21f3649d2ba848efa2d4067532ccb6b2951e5ccb50989ee4a62bf63fa827480e  VIGILOS-1.2-i3-x86_64.iso
```

Independent hashes, metadata and media checks were recorded before the first test in `REPAIRED-ARTIFACTS.json`, then rechecked after all guests shut down. Checksum sidecars and the matching per-edition build-evidence archives are beside the ISOs.

## Repairs and clean-build provenance

1. **PackageKit/Discover:** native PackageKit 1.4's dnf5 backend replaces releasever with the product OS version; the original images therefore requested Fedora 1.2 and returned 404, while DNF used 44. The identity RPM now owns the supported libdnf5 distribution repository override, derived from verified native `fedora-repos` files. Only release-dependent names, URLs and signing-key locations are bound to 44; `$basearch`, upstream repo files, enablement, TLS and signature verification are retained. VIGIL `VERSION_ID=1.2` remains intact, with the Fedora 44 compatibility capability. Native PackageKit/libdnf5 binaries pass RPM verification. See the [versioned native backend](https://github.com/PackageKit/PackageKit/blob/v1.4.0/backends/dnf5/dnf5-backend-utils.cpp#L128-L150) and [supported distribution overrides](https://dnf5.readthedocs.io/en/latest/dnf5.conf.5.html#drop-in-repo-directories).
2. **i3 LXPolKit:** the payload now includes sanitized GTK2 defaults selecting the existing dark theme and the signed native `gtk-murrine-engine` dependency. The actual authorization agent loads Murrine, shows a readable dark dialog and authenticates the normal installed administrator before and after update/reboot. No polkit/PAM or privilege-policy workaround was applied.
3. **KDE wallpaper:** a native new-containment hook sets aspect fit and the matching dark matte when Plasma creates a desktop. It preserves the user's artwork and saved layouts. A first diagnostic fixed-ID seed proved ineffective and was replaced before these final rebuilds; that diagnostic guest/prototype is excluded from acceptance. Actual live/installed wallpaper API reads report FillMode 1, and 1024×768 captures now show the complete mark. The [native new-containment event](https://github.com/KDE/libplasma/blob/Plasma/6.6/src/plasma/corona.cpp#L541-L568) distinguishes creation from restoring saved layouts.

Eight scoped source files are listed in `SOURCE-CHANGES.json`: the repository-override generator/identity packaging, GTK2 defaults/dependency, native wallpaper hook/default installer, removal of the ineffective seed and meaningful source regression checks. Product RPM revisions are identity 1.2-3, KDE branding 1.2-23, i3 branding 1.2-24 and i3 desktop 1.2-5.

The maintained `scripts/build-and-brand.sh --desktop both` completed with exit 0 between **18:23:22 and 18:53:01 UTC**, using an absent private workspace/cache at `/home/bheffernan/Documents/Codex/2026-10-22/task/repair2-20261024/work/build-clean` and a separate new output directory. Both sequential fresh cloud overlays used newly downloaded/verified official pinned Fedora 44 inputs. Public source CDs match all 27 current script files. The fresh overlay backing paths, signed-input bootstrap, package manifests, validation logs, transfer manifests, embedded media checks, hybrid BIOS/UEFI entries and single EFI partition are recorded independently. No original `.build` cache, old lab root, original ISO replacement or test-guest product hotfix supplied a final pass. Later builds can have different hashes when signed upstream packages change.

## Actual acceptance matrix

One disposable guest with 6 GiB RAM and four CPUs ran at a time; fresh installed disks were 48 GiB. Installation used the native GUI, a normal test administrator and a disabled root account. Installed tests booted with no installation ISO attached. Network access was enabled only for package/application checks; cold display and BIOS smoke guests were offline.

| Check | KDE | i3 |
| --- | --- | --- |
| Static checks and fresh build/source provenance | PASS | PASS |
| Independent SHA256, embedded media, BIOS/UEFI ISO structure | PASS | PASS |
| Actual UEFI live desktop and dark Qt/GTK defaults | PASS | PASS |
| Native PackageKit force refresh, live and installed | PASS | PASS |
| Actual Discover user Refresh returns Up to date | PASS, live/installed/after reboot | N/A: Discover not shipped |
| Native signed DNF metadata refresh, upgrade and component reinstall | PASS | PASS |
| Actual fresh UEFI installation and normal installer-exit cleanup | PASS | PASS |
| ISO-free installed boot, native greeter and password login | PASS | PASS |
| Native logout/relogin and graphical reboot, changed boot IDs | PASS | PASS |
| Native lock: wrong password rejected, correct password unlocks | PASS | PASS |
| PackageKit/defaults/native integrity after reinstall and reboot | PASS | PASS |
| Dark LXPolKit and actual admin authentication after reboot | N/A | PASS |
| Helper singletons, logout cleanup, relogin/portal lifecycle | N/A | PASS |
| Brave defaults; i3 shell/runtime/clipboard helpers | PASS | PASS |
| Cold 1024×768,1920×1080,3840×2160 greeter/desktop/lock/unlock | PASS | PASS |
| Boot/Plymouth/greeter/lock branding; KDE splash | PASS | PASS |
| Actual BIOS live boot, normal desktop, EFI absent and Enforcing | PASS | PASS |
| Current failed units, crashes, full current-boot AVC/OOM checks | PASS: no findings | PASS: no findings |
| BIOS installation, physical hardware, Secure Boot | NOT RUN | NOT RUN |
| Independent HiDPI factors or physical multiple monitors | NOT RUN | NOT RUN |

Full installed health evidence is timestamped **19:40:39 UTC KDE** and **20:11:40 UTC i3**; completed native PackageKit transactions were inspected separately afterward. Boot IDs changed from `aacaced1-9edc-4ceb-9a49-0ba74c2446a9` to `798302c8-596e-40de-bad8-74373401ecbd` and from `5ad64b7d-44c6-4677-a0b1-869f223df8a6` to `153880b0-09e8-4dcf-9d66-64b8c3e5ba46` respectively. Actual screenshots and journal/process evidence, rather than filenames or connection state, determine passes.

The i3 regression exercised Alacritty, Git `<main>` prompt, Node 24.18.0/npm 11.16.0, Python 3.14.8, Flatpak 1.18.4 and a known xclip/Greenclip/Rofi fixture. Brave retained normal sandbox/credential behavior and used a nonblank native encrypted-keyring test password. Exactly one each of i3/Polybar/LXPolKit/Greenclip/xss-lock ran; all stopped on logout and returned once on relogin. Both editions retained Enforcing, native repository trust and locked installed root. Native Anaconda's temporary installation policy transition restored normally on Exit.

## Evidence, preservation and limits

Evidence root: `/home/bheffernan/Documents/Codex/2026-10-22/task/repair2-20261024/work/evidence/`.

- Inventory/provenance: `REPAIRED-ARTIFACTS.json`, `BUILD-SOURCE.json`, `SOURCE-CHANGES.json`, `inventory.log`, `{kde,i3}-media/`, `{kde,i3}-clean-build/`.
- Actual installer success: `kde-install-final.png`, `i3-install-completion-check.png`. Native update/PackageKit: `{kde,i3}-native-update-progress.log`, `{kde,i3}-after-reinstall-packagekit-result.log`, `{kde,i3}-final-packagekit-result.log`; actual Discover: `kde-post-reboot-discover-user-refresh.png`.
- Full final health and reboot proof: `{kde,i3}-final-post-reboot-check.log`, `{KDE,I3}-REBOOT-PROOF.json`, `{KDE,I3}-CORE-RESULTS.json`. i3 authorization: `i3-installed-lxpolkit-dark-prompt.png`, `i3-post-reboot-lxpolkit-dark.png`, `i3-post-reboot-lxpolkit-success.png`; lifecycle and runtime captures retain the actual results.
- Native-resolution visuals: `{kde,i3}-{1024x768,1920x1080,3840x2160}-visuals/`. Comparisons: `kde-1024x768-before-after.png`, `i3-lxpolkit-before-after.png`. Real boot frames: `{kde,i3}-bios-boot/early-frames/`, `kde-installed-first-login/`, `i3-installed-first-boot/`. BIOS terminal proof: `{kde,i3}-bios-firmware-kernel-enforcing.png`. Faithful 4K analysis copies avoid misleading automatic image-tool thumbnails; native PNGs remain unchanged.
- `HARNESS-NOTES.md` distinguishes diagnostic failures/prototypes, harmless preliminary wizard clicks, harness-only corrections and native warnings from final product acceptance. `PRESERVATION-BEFORE-DOCS.json`, `PRESERVATION-AFTER-DOCS.json` and `DOC-WRITES.json` record final fences and the narrowly scoped documentation updates.

The original manual folder `.build/output/20261024T062157Z`, diagnostic attempt folder `.build/output/repair-20261024T172717Z`, their exact ISO bytes/metadata/checksum sidecars and the original manual `.build/LATEST.json` are preserved. Original Git contents, metadata and xattrs, user artwork and the two protected legacy ISO metadata records are preserved; protected contents were not accessed. Current product source matches the final build snapshot, with only the declared report/handoff documentation changes afterward. Recoverable pre-repair source backup: `/home/bheffernan/Documents/Codex/2026-10-22/task/repair-20261024/work/recovery/source-before-repairs.tar`, SHA256 `c0004ae38f4c0da972b54156c759c64fa11c59d81e3d0db3bc6a7c4d50398fd5`. Original Git remains in place; no commit, push or release publication was performed. All owned build/test VMs are confirmed off. One i3 widescreen instance ended during an execution-transport disconnect; its captured login/lock tests completed, but its shutdown is recorded as interrupted/unknown. After reconnection, a separate cold 4K boot and complete installed recovery health check passed, followed by normal shutdown. See `RECONNECTION.json` and `i3-after-interruption-recovery-check.log`.

No scoped repair blocker remains. Journals are not warning-free: native virtual-CD/IRQ/Bluetooth, Qt/portal/AppStream warnings, i3 transient IM settings service exits and KDE native DNF systemd-scriptlet bus warnings are retained. Subsequent native file integrity, normal session/reboot behavior and complete security/crash checks passed; these warnings were not hidden or corrected by security changes. The IM settings exits also occur in the original manual-image logs; tested text input worked, while broader input-method coverage is untested. Native SDDM's redundant global avatar overwrite remains an earlier nonblocking packaging observation outside these three repairs; theme-owned branding survives native reinstallation. The VM matrix does not establish universal hardware compatibility, driver support, every application feature, Secure Boot or a public production release. Host OS/login/security/network settings were not changed by this repair.

## Repeat validation

Verify these exact repaired bytes:

```bash
cd /home/bheffernan/Project/VigilOS/.build/output/repair-20261024T182322Z
sha256sum -c VIGILOS-1.2-kde-x86_64.iso.sha256 VIGILOS-1.2-i3-x86_64.iso.sha256
```

For a new clean rebuild, run from this project as the normal host user, choosing unused workspace/output paths and no cache override:

```bash
bash scripts/build-and-brand.sh --desktop both --workspace /path/to/new-private-workspace --output /path/to/new-output
```

For acceptance, select a new private `VIGIL_TEST_ROOT` per edition, set `VIGIL_EXECUTION_APPROVED=1`, `VIGIL_FIRMWARE=uefi`, `VIGIL_DISPLAY_MODE=1280x800` and use `scripts/test-vm.sh live vigil /absolute/repaired.iso`. Finish a fresh native installation, power off normally, then use `scripts/test-vm.sh installed vigil` with the same test root and no ISO. Keep the one-guest resource limit. In the disposable guest, exercise `pkcon refresh force`, Discover's user Refresh on KDE and signed native DNF updates; inspect actual completed results. Preserve source/artifact hashes and screenshots. See [BUILD.md](BUILD.md) and the retained finite test harness/evidence for detailed reproduction.
