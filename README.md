# VIGIL OS

VIGIL OS is a Linux distribution based on Fedora 44, created by Brad Heffernan. It comes in two editions: KDE Plasma on Wayland, and i3 on X11. Both use the dark VIGIL artwork on the boot, login and lock screens and in the installer, with a lighter landscape painting by [byrotek](https://www.deviantart.com/byrotek) on the desktop, used with the artist's permission. Both default to dark themes and the white Qogir cursor.

The KDE edition includes SDDM, Dolphin, Konsole, Kate and Discover. The i3 edition includes LightDM, Polybar, Rofi, i3lock-color, Greenclip, Alacritty and Thunar. Both come with Brave as the default browser, LibreOffice, Node.js, npm, Python, Flatpak and VIGIL Ask. System updates come from the signed Fedora and Brave repositories through RPM and DNF5.

VIGIL OS is still in development. Both 1.8 editions passed BIOS and UEFI live boot, a fresh UEFI install, booting without the ISO, login, lock/unlock and reboot in virtual machines. Both passed all 45 VIGIL Ask tests and the signed VpM example-package workflow, with SELinux enforcing and no denials or failed system/user services. Ask sign-in, streaming, follow-up, Stop and sign-out were exercised against a local test server; production sign-in and billing remain to be qualified. Physical hardware, Secure Boot, BIOS installation, HiDPI and multi-monitor setups remain untested, and DNF update acceptance was not repeated for 1.8. Passing the source checks does not qualify a new ISO; each build needs testing.

## Screenshots

Version 1.8 (Loopback), captured from installed systems at native 1920×1080.

### KDE Plasma

![VIGIL OS 1.8 KDE Plasma desktop](images/kde-desktop-1.8.png)

| Application menu | Welcome Center |
| --- | --- |
| ![KDE application menu](images/kde-menu-1.8.png) | ![Installed KDE desktop and Welcome Center](images/kde-welcome-1.8.png) |

| Login | Lock screen |
| --- | --- |
| ![KDE SDDM login screen](images/kde-login-1.8.png) | ![KDE lock screen](images/kde-lock-1.8.png) |

### i3

![VIGIL OS 1.8 i3 desktop with Polybar](images/i3-desktop-1.8.png)

| Application launcher | Login |
| --- | --- |
| ![i3 application launcher](images/i3-menu-1.8.png) | ![i3 LightDM login screen](images/i3-login-1.8.png) |

![i3 lock screen](images/i3-lock-1.8.png)

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

On both installed 1.8 editions, the `hello` example passed reproducible builds, encrypted-key signing, dry-run planning, refusal to install while switched off, signed installation with its sandboxed script, execution, verification and removal. The running-system switch was removed afterward.

| VpM results on KDE | VpM results on i3 |
| --- | --- |
| ![VpM installation, verification and removal results in Konsole](images/kde-vpm-1.8.png) | ![VpM installation, verification and removal results in Alacritty](images/i3-vpm-1.8.png) |

When a VpM checkout sits next to this repository in `../VpM`, the ISO build compiles and tests it on this machine and installs it in both editions as the `vpm` RPM. That needs cargo, git, a C compiler and `sqlite-devel`, and the checkout must have no uncommitted changes. `--vpm DIR` uses a checkout somewhere else and `--no-vpm` leaves VpM out. On the installed system, `man vpm` is the reference and `/usr/share/vpm/examples/hello` is an example package to build.

To test a VpM checkout in a throwaway VM:

```bash
bash scripts/test-vpm.sh                 # VpM checkout in ../VpM
bash scripts/test-vpm.sh --vpm DIR       # a checkout somewhere else
bash scripts/test-vpm.sh --points ''     # skip the power-cut tests
```

The script boots the same verified Fedora 44 Cloud image the builds use, and builds VpM and its test packages on this machine. It then runs VpM's system tests as root inside the VM, with SELinux enforcing. For each power-cut test it pauses an install or removal, kills the VM, boots it again and checks that VpM recovers. Nothing is installed on this machine, and the results go in `.build/vpm-test/`.

## VIGIL Ask

VIGIL Ask is a small window for quick questions, answered by [VIGIL GLM](https://vigilglm.ai). **Sign in** shows a short code and opens VIGIL GLM in your browser, where you sign in with email, Google or GitHub (or create a free account), enter the code and connect VIGIL Ask. There's no API key to create, and VIGIL Ask never sees your password. `vigil-ask signin` does the same from a terminal. Questions, and anything you attach, are answered in the cloud by GLM models from Z.ai and use your account's credits, within its plan's limits. The window shows how much of the 5-hour and weekly limits you've used.

The connection can only ask text questions, read the account's name and email and show usage; VIGIL GLM keeps tools, browsing, files and saved memories off for it, and VIGIL Ask has no local command tools either. Its tokens are kept in a file only you can read. **Sign out** deletes them and ends the connection on VIGIL GLM, and you can also remove it there under Settings → Accounts → Connected desktops. Real-account sign-in, credits and history behaviour still need acceptance with a test account.

On i3, Super+Shift+A asks through Rofi and Super+Ctrl+A attaches the selected text. Polybar shows the status, and Thunar's Send To menu attaches files. On Plasma, Meta+Alt+A opens the window, Meta+Alt+Shift+A attaches the selected text, and typing `ask` and a question in KRunner sends it. Dolphin's Actions menu attaches text files on both editions. Locking the screen or logging out stops an answer in progress. `man vigil-ask` has the details, and `bash scripts/test-vigil-ask.sh` tests it in a throwaway Fedora 44 VM, with results in `.build/vigil-ask-test/`. Its nested Plasma checks need an existing usable EGL render node for the virtual GPU (`VIGIL_TEST_RENDER_NODE`, default `/dev/dri/renderD128`); the runner makes no host graphics or permission changes.

| VIGIL Ask on KDE | VIGIL Ask on i3 |
| --- | --- |
| ![VIGIL Ask opening the real VIGIL GLM sign-in page on KDE](images/kde-ask-signin-1.8.png) | ![VIGIL Ask opening the real VIGIL GLM sign-in page on i3](images/i3-ask-signin-1.8.png) |

These 1.8 screenshots show the earlier in-window sign-in page, which the browser code has replaced.

## Future plans

SIERRA desktop integration is planned: a search field in Plasma, a Rofi prompt in i3, and a task window shared by both. The first version would handle conversation, selected files and a few tested application actions, each with explicit permission. General GUI automation would stay experimental. None of this is implemented yet.

## Credits

The desktop wallpaper is a painting by [byrotek](https://www.deviantart.com/byrotek), used in VIGIL OS. You can find more of his artwork on [his DeviantArt profile](https://www.deviantart.com/byrotek). The painting isn't covered by the VIGIL licence, and this credit must stay with it.

## Licence

VIGIL-owned original material is available under the [VIGIL Personal Build Licence](LICENSE). It permits cloning and building an unmodified copy for personal use, with the documented build and version settings. It requires the branding to remain intact and prohibits commercial redistribution, modification and reuse of covered material in other projects.

These are source-available terms. Fedora, imported software and artwork retain their own licences, and the desktop wallpaper by byrotek is not covered by the VIGIL terms. Existing GPL grants and rights in GPL-covered derivatives remain in effect; the VIGIL terms do not override them. See [LICENSES](LICENSES) and the notices supplied with individual components.

## Developer

Created and maintained by Brad Heffernan for [VIGIL GLM](https://vigilglm.ai).
