# Build VIGIL OS KDE and i3

From the project directory, run:

```bash
bash scripts/build-and-brand.sh
```

This builds **both separate editions**. Use `--desktop kde` or `--desktop i3` for one edition. `--check` validates prerequisites and source without downloading or starting a VM.

The command downloads and verifies the pinned official Fedora 44 KDE ISO and Cloud image using the Fedora 44 signing fingerprint and SHA256 checksums. For each edition it boots a fresh disposable cloud overlay, installs build tools inside that VM, updates a fresh extracted official live root through signed repositories, applies the product packages and theme, generates a matching live initramfs, packs SELinux-labelled EROFS and assembles/checks the hybrid BIOS/UEFI ISO. The i3 edition replaces Plasma/SDDM with i3/LightDM and includes the imported portable user theme. Both use the same VIGIL City image.

The host needs Python3, Bash, curl, gpgv, OpenSSH client/keygen, xorriso, QEMU/qemu-img and existing usable KVM. The script reports missing prerequisites instead of changing host packages, services, permissions or security settings. No root host command, physical disk, shared host directory or personal SSH key is used. Builders use 6 GiB RAM and four CPUs, one at a time. Each disposable overlay has 104 GiB virtual capacity; completed/failed runs are retained for inspection. Allow sufficient disk space for each edition and retain the cache if rebuilding.

`.build/output/<UTC timestamp>/` holds the ISO/checksum/evidence archive; `.build/run-<UTC timestamp>/` holds detailed logs and private ephemeral builder credentials. `.build/LATEST.json` is written only after the requested editions finish. Set `--workspace /path/to/private-workspace` and optionally `--cache /path/to/cache` or `--output /new/output/directory`. Existing outputs are never overwritten. Keep `.build` private and out of source control or public archives.

## i3 edition

Your colors, gaps, keybindings, Rofi themes, Alacritty colors, Git prompt and useful local controls are imported into `branding/i3`. Fixed monitor layouts, personal app bindings/exports, NVIDIA-only Polybar modules and unused host hooks are excluded. Your GTK theme, icon/cursor themes and notification colors are included. The cleaned Bash settings load through Fedora’s native `.bashrc.d` mechanism, preserving the signed package-owned `.bashrc`; the Git prompt helper is copied to the user home. Public fonts and upstream licenses are included. Greenclip4.2 and i3lock-color2.13.c.5 are pinned and hash-checked; the color lock is compiled in the disposable builder and uses Fedora's existing i3lock PAM authentication. Personal Chromium profiles, keys, clipboard history and caches are never imported.

Super+Enter opens Alacritty, Super+Q Brave, Super+E Thunar, Super+D Rofi, Super+Z clipboard history, Super+X power menu and Super+L the lock screen. Super+Shift+I opens the live installer; its Polybar button appears only in the live environment. The default login session is **VIGIL OS i3**. It keeps xss-lock alive throughout the desktop session and stops its own locker before X shuts down. New Greenclip configurations use a private per-user cache and contain no imported history or migration message. New installed users receive writable clean configs. All desktop, greeter and lock-screen wallpaper paths use the same product image.

## Scripts

- `build-and-brand.sh`: the only build entry point; host orchestration in `lib/build.py`.
- `validate.sh`: unprivileged syntax, asset, import and configuration checks.
- `test-vm.sh`: optional isolated manual acceptance VM launcher.
- `lib/`: build implementation and packaging helpers, guarded against accidental host execution.
- `runtime/`: product helpers installed into the resulting image.

Superseded composer/livecd alternatives, old wrappers and host cleanup/setup scripts were removed from the active script directory. A recovery archive of the previous scripts is retained with the task evidence. Historical validation records describe candidate033 and must not be treated as fresh acceptance of these new builds. See [the fresh-build validation record](VALIDATION-2026-10-22.md) for current hashes, actual results and testing limits.
