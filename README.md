# VIGIL OS

VIGIL OS is a Linux distribution based on Fedora 44, created by Brad Heffernan. It comes in two editions: KDE Plasma on Wayland, and i3 on X11. Both use the dark VIGIL artwork on the boot, login and lock screens and in the installer, with a lighter landscape painting by [byrotek](https://www.deviantart.com/byrotek) on the desktop, used with the artist's permission. Both default to dark themes and the white Qogir cursor.

The KDE edition includes SDDM, Dolphin, Konsole, Kate and Discover. The i3 edition includes LightDM, Polybar, Rofi, i3lock-color, Greenclip, Alacritty and Thunar. Both come with Brave as the default browser, LibreOffice, Node.js, npm, Python and Flatpak. System updates come from the signed Fedora and Brave repositories through RPM and DNF5.

VIGIL OS is still in development. The 1.2 images passed these tests in virtual machines: live boot with BIOS and UEFI, a fresh UEFI install, logging in to and rebooting the installed system, updates, unlocking the lock screen, and display checks. They have not been tested on physical hardware or with Secure Boot. Passing the source checks doesn't mean a new ISO works; each new build still needs testing.

## Screenshots

### KDE Plasma

![VIGIL OS KDE Plasma desktop](images/KDE-Desktop.png)

| Application menu | Live environment |
| --- | --- |
| ![KDE application menu](images/KDE-Menu.png) | ![KDE live desktop and welcome window](images/KDE-Live.png) |

### i3

| Desktop | Login |
| --- | --- |
| ![VIGIL OS i3 desktop with Polybar](images/i3-desktop.png) | ![VIGIL OS i3 LightDM login screen](images/i3-login.png) |

## Building the ISO

You need Bash, Python 3, curl, gpgv, the OpenSSH client tools, xorriso, QEMU with qemu-img, and working KVM access. Run the build as your normal user from the repository directory:

```bash
bash scripts/build-and-brand.sh
```

That builds both editions, one after the other. To build one edition, or to check the source and host tools without building anything:

```bash
bash scripts/build-and-brand.sh --desktop kde
bash scripts/build-and-brand.sh --desktop i3
bash scripts/build-and-brand.sh --check
```

The script checks the Fedora downloads against Fedora's signed checksums, then builds each edition in a fresh throwaway VM with 6 GiB of RAM and four CPUs. Installing packages, mounting images and preparing the image all happen inside that VM. If a host tool is missing, the script names it and stops; it never installs anything on your machine.

Finished ISOs, their SHA256 checksums and the build evidence go in `.build/output/<timestamp>/`, and earlier builds are never overwritten. Logs and the temporary VM files stay in `.build/`, which must not be published. `bash scripts/build-and-brand.sh --help` lists the options for the workspace, cache and output folders.

Version numbers have the form `build_number.version_number`. For a bigger release you change the first number and the codename by hand in `version.json`. Each real build adds one to the second number, both editions built together get the same number, and `1.9` is followed by `1.10`. Checks don't change it, and neither does deleting `.build`. A build that fails after taking a number still uses that number up.

## VpM, the VIGIL OS package manager

VpM is the package manager being written for VIGIL OS. It is developed in its own repository, which isn't public yet. VpM packages install under `/opt/vpm`, next to RPM, and RPM and DNF5 stay in charge of the rest of the system.

VpM can already build, sign and verify packages, and install and remove them with SELinux labels and sandboxed install scripts. So far it has changed a running system only inside test VMs. On an installed system it stays switched off until an administrator creates `/etc/vpm/allow-running-system`.

When a VpM checkout sits next to this repository in `../VpM`, the ISO build compiles and tests it on this machine and installs it in both editions as the `vpm` RPM. That needs cargo, git, a C compiler and `sqlite-devel`, and the checkout must have no uncommitted changes. `--vpm DIR` uses a checkout somewhere else and `--no-vpm` leaves VpM out. On the installed system, `man vpm` is the reference and `/usr/share/vpm/examples/hello` is an example package to build.

To test a VpM checkout in a throwaway VM:

```bash
bash scripts/test-vpm.sh                 # VpM checkout in ../VpM
bash scripts/test-vpm.sh --vpm DIR       # a checkout somewhere else
bash scripts/test-vpm.sh --points ''     # skip the power-cut tests
```

The script boots the same verified Fedora 44 Cloud image the builds use, and builds VpM and its test packages on this machine. It then runs VpM's system tests as root inside the VM, with SELinux enforcing. For each power-cut test it pauses an install or removal, kills the VM, boots it again and checks that VpM recovers. Nothing is installed on this machine, and the results go in `.build/vpm-test/`.

## Future plans

SIERRA desktop integration is planned: a search field in Plasma, a Rofi prompt in i3, and a task window shared by both. The first version would handle conversation, selected files and a few tested application actions, each with explicit permission. General GUI automation would stay experimental. None of this is implemented yet.

## Credits

The desktop wallpaper is a painting by [byrotek](https://www.deviantart.com/byrotek), used in VIGIL OS. You can find more of his artwork on [his DeviantArt profile](https://www.deviantart.com/byrotek). The painting isn't covered by the VIGIL licence, and this credit must stay with it.

## Licence

VIGIL-owned original material is available under the [VIGIL Personal Build Licence](LICENSE). It permits cloning and building an unmodified copy for personal use, with the documented build and version settings. It requires the branding to remain intact and prohibits commercial redistribution, modification and reuse of covered material in other projects.

These are source-available terms. Fedora, imported software and artwork retain their own licences, and the desktop wallpaper by byrotek is not covered by the VIGIL terms. Existing GPL grants and rights in GPL-covered derivatives remain in effect; the VIGIL terms do not override them. See [LICENSES](LICENSES) and the notices supplied with individual components.

## Developer

Created and maintained by Brad Heffernan for [VIGIL GLM](https://vigilglm.ai).
