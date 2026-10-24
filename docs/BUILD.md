# Build VIGIL OS KDE and i3

From the project directory, run:

```bash
bash scripts/build-and-brand.sh
```

This builds **both separate editions**. Use `--desktop kde` or `--desktop i3` for one edition. `--check` validates prerequisites and source without downloading or starting a VM.

The command downloads and verifies the pinned official Fedora 44 KDE ISO and Cloud image using the Fedora 44 signing fingerprint and SHA256 checksums. For each edition it boots a fresh disposable cloud overlay, installs build tools inside that VM, updates a fresh extracted official live root through signed repositories, applies the product packages and theme, generates a matching live initramfs, packs SELinux-labelled EROFS and assembles/checks the hybrid BIOS/UEFI ISO. The i3 edition replaces Plasma/SDDM with i3/LightDM and includes the imported portable user theme. Both use the supplied dark faded VIGIL mark. KDE uses PurPurNight Plasma, the VIGIL Dark Qt palette and shared dark GTK defaults. The user-updated SDDM background is preserved.

The host needs Python3, Bash, curl, gpgv, OpenSSH client/keygen, xorriso, QEMU/qemu-img and existing usable KVM. The script reports missing prerequisites instead of changing host packages, services, permissions or security settings. No root host command, physical disk, shared host directory or personal SSH key is used. Builders use 6 GiB RAM and four CPUs, one at a time. Each disposable overlay has 104 GiB virtual capacity; completed/failed runs are retained for inspection. Allow sufficient disk space for each edition and retain the cache if rebuilding.

`.build/output/<UTC timestamp>/` holds the ISO/checksum/evidence archive; `.build/run-<UTC timestamp>/` holds detailed logs and private ephemeral builder credentials. `.build/LATEST.json` is written only after the requested editions finish. Set `--workspace /path/to/private-workspace` and optionally `--cache /path/to/cache` or `--output /new/output/directory`. Existing outputs are never overwritten. Keep `.build` private and out of source control or public archives.

PackageKit and Discover use the verified Fedora base release through a product-owned libdnf5 distribution repository override; VIGIL `VERSION_ID` follows the allocated product version. Native Fedora repository files and signature/TLS settings remain intact. The i3 payload includes its GTK2 dark defaults and native Murrine engine for LXPolKit, retaining upstream authentication. Newly created Plasma desktops receive aspect-fit wallpaper with a matching dark matte through the native containment-creation hook; existing saved layouts are not reset on login.

## Version numbering

The product format is **build_number.version_number**. The first number and codename are selected manually; the second number advances once per real build invocation. KDE and i3 share that version when built together. The sequence uses integers: `1.9` is followed by `1.10`.

The initial project-root `version.json` was configured as follows; its counter advances with real builds:

```json
{
  "build_number": 1,
  "codename": "Loopback",
  "next_version_number": 3
}
```

The next build reserves `1.3 (Loopback)` and atomically advances `next_version_number` to 4. A following build reserves 1.4. The file lives outside `.build`, so a clean rebuild or a different `--workspace` retains the counter. Preserve this file when cleaning or moving the source. Builds do not create Git commits.

When a larger feature build is ready, manually edit the first number and codename. To begin at `2.0`, for example:

```json
{
  "build_number": 2,
  "codename": "Your New Codename",
  "next_version_number": 0
}
```

Only reset the second-number counter when intentionally starting a new first-number series. The script never changes the selected first number or codename.

`--check`, missing prerequisites, invalid configuration and failed input verification do not consume a version. After verified inputs and output preflight, a real build reserves its version before starting a builder. Failure or interruption after reservation consumes that number, including a partial two-edition run; later runs use the next number and do not relabel existing artifacts. The checkout-wide `.vigil-build.lock` prevents concurrent invocations using different workspaces; the existing workspace lock also prevents two checkouts from sharing a busy workspace.

Each run saves immutable `release.json` and `version.json` snapshots. Both source CDs use those snapshots, so later manual edits cannot change the second edition's allocated version. The version follows ISO names/volume labels, OS identity/banners, Anaconda's build stamp, live/installed GRUB labels, product RPM versions/dependencies and artifact receipts. The generated `/usr/lib/vigilos/release.json`, evidence archive, run receipt and `LATEST.json` identify the same version/build ID. Fedora repository/signing compatibility remains 44; package `Release` revisions remain separate from the product numbering.

`bash scripts/validate.sh` includes temporary-fixture regression tests for allocation, failed/concurrent runs, clean-workspace persistence, source-CD metadata, rendered identity and native RPM spec parsing when available. Full ISO builds and VM runtime acceptance remain separate. The existing accepted 1.2 ISO files are preserved; this numbering change has not produced a new 1.3 ISO. See [the versioning validation record](VERSIONING-2026-10-25.md).

## i3 edition

Your colors, gaps, keybindings, Rofi themes, Alacritty colors, Git prompt and useful local controls are imported into `branding/i3`. Fixed monitor layouts, personal app bindings/exports, NVIDIA-only Polybar modules and unused host hooks are excluded. Your GTK theme, icon/cursor themes and notification colors are included. The cleaned Bash settings load through Fedora’s native `.bashrc.d` mechanism, preserving the signed package-owned `.bashrc`; the Git prompt helper is copied to the user home. Public fonts and upstream licenses are included. Greenclip4.2 and i3lock-color2.13.c.5 are pinned and hash-checked; the color lock is compiled in the disposable builder and uses Fedora's existing i3lock PAM authentication. Personal Chromium profiles, keys, clipboard history and caches are never imported.

Super+Enter opens Alacritty, Super+Q Brave, Super+E Thunar, Super+D Rofi, Super+Z clipboard history, Super+X power menu and Super+L the lock screen. Super+Shift+I opens the live installer; its Polybar button appears only in the live environment. The default login session is **VIGIL OS i3**. Its Qt applications use the native GTK3 theme bridge. An unprivileged i3 session target manages the ordinary desktop portals and stops graphical-only services on logout; the GTK backend is selected for i3. It keeps xss-lock alive throughout the desktop session and stops its own locker before X shuts down. New Greenclip configurations use a private per-user cache and contain no imported history or migration message. New installed users receive writable clean configs. All desktop, greeter and lock-screen wallpaper paths use the same product image.

## Scripts

- `build-and-brand.sh`: the only build entry point; host orchestration in `lib/build.py`.
- `validate.sh`: unprivileged syntax, asset, import and configuration checks.
- `test-vm.sh`: optional isolated manual acceptance VM launcher.
- `lib/`: build implementation and packaging helpers, guarded against accidental host execution.
- `runtime/`: product helpers installed into the resulting image.

Superseded composer/livecd alternatives, old wrappers and host cleanup/setup scripts were removed from the active script directory. A recovery archive of the previous scripts is retained with the task evidence. Historical validation records describe candidate033 and must not be treated as fresh acceptance of these new builds. See [the repaired-build validation](REPAIRED-BUILD-VALIDATION-2026-10-24.md) for the current separate clean rebuilds and completed VM acceptance. The [original manual-build verification](MANUAL-BUILD-VALIDATION-2026-10-24.md) preserves the original images and their three failures. The [dark-theme validation record](DARK-THEME-VALIDATION.md) and [22 October script-cleanup record](VALIDATION-2026-10-22.md) describe earlier artifacts.

## Future SIERRA integration

The [SIERRA integration plan](SIERRA-INTEGRATION-PLAN.md) is documentation for future development only. This build does not implement SIERRA.
