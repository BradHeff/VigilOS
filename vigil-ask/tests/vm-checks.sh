#!/bin/bash
# Runs inside the disposable VIGIL Ask test VM as the unprivileged builder user.
set -uo pipefail
M=/ask-test
OUT=$HOME/out
mkdir -p "$OUT"
check() {
    local name=$1; shift
    { echo "== $name"; "$@"; } >>"$OUT/checks.log" 2>&1 && echo "PASS: $name" || echo "FAIL: $name"
}
installed() { python3 -I -c "import sys; sys.path.insert(0, '/usr/share/vigil-ask'); $1"; }
case ${1:-} in
package)
    rm -rf ~/rpmbuild && mkdir -p ~/rpmbuild/SOURCES && cp -a "$M/SOURCES/." ~/rpmbuild/SOURCES/
    check 'vigil-ask RPM builds' rpmbuild --define "_topdir $HOME/rpmbuild" -bb "$M/vigil-ask.spec"
    check 'vigil-ask RPM installs' bash -c 'sudo dnf -y install ~/rpmbuild/RPMS/noarch/vigil-ask-*.rpm'
    check 'installed files verify' rpm -V vigil-ask
    check 'Claude Code repository ships turned off' bash -c '! dnf -q repolist --enabled | grep -qw claude-code && dnf -q repolist --disabled | grep -qw claude-code'
    check 'routine refresh leaves the Claude Code repository alone' bash -c 'sudo dnf makecache --refresh >"$HOME/out/makecache.log" 2>&1 && grep -q "Fedora 44" "$HOME/out/makecache.log" && ! grep -qi claude "$HOME/out/makecache.log"'
    check 'desktop entries are valid' desktop-file-validate /usr/share/applications/org.vigilos.Ask.desktop /usr/share/Thunar/sendto/org.vigilos.Ask.desktop
    check 'byte-compiled modules are owned by the package' bash -c 'rpm -ql vigil-ask | grep -q "vigil_ask/__pycache__/core.cpython-.*\.pyc$"'
    check 'installing Claude Code needs an administrator' bash -c 'pkaction --verbose --action-id org.vigilos.ask.install-claude-code | grep -Eq "implicit active: +auth_admin$"'
    check 'status is missing before Claude Code is installed' bash -c '[[ $(vigil-ask status) == missing ]]'
    ;;
unit)
    check 'unit and window tests pass with PySide6' env QT_QPA_PLATFORM=offscreen VIGIL_ASK_REQUIRE_WINDOW=1 \
        VIGIL_ASK_SCREENSHOT="$OUT/window-fake-claude.png" python3 -B "$M/source/vigil-ask/tests/test_vigil_ask.py"
    check 'setup screen renders: not installed' env QT_QPA_PLATFORM=offscreen python3 -I "$M/source/vigil-ask/tests/vm-shot.py" "$OUT/setup-missing.png" missing
    ;;
i3)
    check 'i3 test packages install' sudo dnf -y install i3 polybar rofi xclip xrandr xorg-x11-server-Xvfb xdotool ImageMagick
    mkdir -p ~/.config ~/.local/share/fonts
    cp -a "$M/i3/config/." ~/.config/
    cp "$M"/i3/fonts/*.ttf ~/.local/share/fonts/ && fc-cache -f
    export DISPLAY=:99
    Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp >"$OUT/xvfb.log" 2>&1 &
    for _ in {1..50}; do xrandr --query >/dev/null 2>&1 && break; sleep 0.2; done
    i3 -c ~/.config/i3/config >"$OUT/i3.log" 2>&1 &
    for _ in {1..50}; do i3-msg -t get_version >/dev/null 2>&1 && break; sleep 0.2; done
    sleep 3
    pgrep -u "$USER" -x polybar >/dev/null || { polybar main --config="$HOME/.config/polybar/config.ini" >"$OUT/polybar.log" 2>&1 & }
    waitfor() { for _ in {1..75}; do pgrep -u "$USER" "$@" >/dev/null && return 0; sleep 0.2; done; return 1; }
    windows() { python3 -I -c 'import json, subprocess, sys, time
deadline = time.monotonic() + 30
while True:
    found = []
    def walk(node, floating=False):
        floating = floating or node.get("type") == "floating_con"
        if (node.get("window_properties") or {}).get("class") == "vigil-ask-window":
            found.append((node["rect"], floating))
        for child in node.get("nodes", []) + node.get("floating_nodes", []):
            walk(child, floating)
    walk(json.loads(subprocess.run(["i3-msg", "-t", "get_tree"], capture_output=True, text=True).stdout))
    if found or time.monotonic() > deadline:
        break
    time.sleep(0.5)
print(found)
centred = [abs(r["x"] + r["width"] / 2 - 960) < 60 and abs(r["y"] + r["height"] / 2 - 540) < 80 for r, f in found]
sys.exit(not (len(found) == 1 and found[0][1] and all(centred)))'; }
    check 'Polybar runs the VIGIL Ask status module' waitfor -f 'vigil-ask status --follow --polybar'
    import -window root "$OUT/i3-bar.png"
    xdotool key super+shift+a
    check 'Super+Shift+A opens the Rofi prompt' waitfor -x rofi
    sleep 1
    xdotool type --delay 40 'What does i3 do?'
    import -window root "$OUT/i3-rofi.png"
    xdotool key Return
    check 'the question opens one floating, centred window' windows
    sleep 3
    import -window root "$OUT/i3-window.png"
    printf 'selected words' | xclip -selection primary
    xdotool key super+ctrl+a
    sleep 3
    check 'Super+Ctrl+A reuses the same window' windows
    import -window root "$OUT/i3-selection.png"
    check 'vigil-ask cancel is harmless with nothing running' vigil-ask cancel
    i3-msg exit >/dev/null 2>&1
    pkill -u "$USER" -x xclip; pkill -u "$USER" -x Xvfb
    sleep 2
    check 'no VIGIL Ask processes outlive the session' bash -c '! pgrep -u "$USER" -f "vigil-ask (window|prompt|status)"'
    ;;
install)
    check 'Claude Code installs through the VIGIL Ask helper' sudo /usr/libexec/vigil-ask/install-claude-code
    check 'pinned Anthropic key imported' bash -c '{ rpmkeys --list; rpm -q gpg-pubkey --qf "%{VERSION} %{SUMMARY}\n"; } 2>/dev/null | tee -a /dev/stderr | grep -qi 1a7ecace'
    check 'repository on after install' bash -c 'dnf -q repolist --enabled | grep -qw claude-code'
    check 'Claude Code meets the minimum version' installed 'import subprocess; from vigil_ask import core, claude_code
found = core.parse_version(subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout); print(found)
sys.exit(not found or found < claude_code.MIN_VERSION)'
    check 'system updates run clean with the repository on' sudo dnf -y upgrade --refresh
    ;;
signedout)
    check 'status is idle once installed' bash -c '[[ $(vigil-ask status) == idle ]]'
    check 'setup shows the cloud notice, then sign-in' installed 'from vigil_ask import core
first = core.setup_state()[0]; core.save_config(notice_accepted=True); second = core.setup_state()[0]; print(first, second)
sys.exit((first, second) != ("notice", "signin"))'
    check 'real Claude Code accepts the Quick Ask flags and reports sign-in' installed 'import queue; from vigil_ask import core, claude_code
run = claude_code.Run(core.claude_path(), "Say ready.")
while (event := run.events.get(timeout=120))[0] != "end": print(event)
print(event, list(run.errors)); sys.exit(event[1]["state"] != "signin" or any("unknown option" in e for e in run.errors))'
    check 'terminal ask points to sign-in' bash -c 'vigil-ask ask hello </dev/null; [[ $? == 2 ]]'
    check 'setup screen renders: sign in' env QT_QPA_PLATFORM=offscreen python3 -I "$M/source/vigil-ask/tests/vm-shot.py" "$OUT/setup-signin.png" signin
    ;;
system)
    check 'SELinux enforcing' bash -c '[[ $(getenforce) == Enforcing ]]'
    check 'no AVC denials' bash -c '! sudo journalctl -b --no-pager | grep -q "avc:  denied" && ! sudo grep -qs denied /var/log/audit/audit.log'
    check 'no failed units' bash -c '[[ -z $(systemctl --failed --no-legend) ]]'
    check 'installed files still verify' rpm -V vigil-ask
    ;;
*) echo "usage: vm-checks.sh package|unit|i3|install|signedout|system" >&2; exit 2 ;;
esac
