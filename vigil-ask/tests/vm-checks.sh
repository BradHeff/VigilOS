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
    check 'the package brings no Claude Code, repository or helper' bash -c '! rpm -qR vigil-ask | grep -qi -e claude -e polkit &&
        ! rpm -ql vigil-ask | grep -qi -e claude -e yum.repos.d -e libexec -e polkit && ! dnf -q repolist --all | grep -qi claude'
    check 'desktop entries are valid' desktop-file-validate /usr/share/applications/org.vigilos.Ask.desktop /usr/share/Thunar/sendto/org.vigilos.Ask.desktop
    check 'byte-compiled modules are owned by the package' bash -c 'rpm -ql vigil-ask | grep -q "vigil_ask/__pycache__/core.cpython-.*\.pyc$"'
    check 'the sign-in dialog loads' installed 'import vigil_ask.signin'
    check 'status is signin before signing in' bash -c '[[ $(vigil-ask status) == signin ]]'
    ;;
unit)
    check 'unit, window and sign-in tests pass with PySide6' env QT_QPA_PLATFORM=offscreen VIGIL_ASK_REQUIRE_WINDOW=1 \
        VIGIL_ASK_SCREENSHOT="$OUT/window-fake-vigil.png" VIGIL_ASK_SIGNIN_SCREENSHOT="$OUT/window-signed-in.png" \
        VIGIL_ASK_CODE_SCREENSHOT="$OUT/signin-code-fake.png" \
        python3 -B "$M/source/vigil-ask/tests/test_vigil_ask.py"
    check 'setup screen renders: notice' env QT_QPA_PLATFORM=offscreen python3 -I "$M/source/vigil-ask/tests/vm-shot.py" "$OUT/setup-notice.png" notice
    ;;
i3)
    check 'i3 test packages install' sudo dnf -y install i3 polybar rofi xclip xrandr xorg-x11-server-Xvfb xdotool ImageMagick
    mkdir -p ~/.config ~/.local/share/fonts
    cp -a "$M/i3/config/." ~/.config/
    cp "$M"/i3/fonts/*.ttf ~/.local/share/fonts/ && fc-cache -f
    # The edition's bar and session scripts, as the i3 RPM installs them.
    sudo install -m0755 "$M"/i3/bin/* /usr/local/bin/
    sudo install -Dm0755 "$M/i3/vigilos-is-live" /usr/local/libexec/vigilos-is-live
    check 'every script the bar runs is installed' bash -c 'for c in $(sed -n "s/^exec = \([^ ]*\).*/\1/p" ~/.config/polybar/config.ini); do
        command -v "$c" || { echo "missing: $c"; exit 1; }; done'
    export DISPLAY=:99
    Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp >"$OUT/xvfb.log" 2>&1 &
    for _ in {1..150}; do xrandr --query >/dev/null 2>&1 && break; sleep 0.2; done
    i3 -c ~/.config/i3/config >"$OUT/i3.log" 2>&1 &
    for _ in {1..150}; do i3-msg -t get_version >/dev/null 2>&1 && break; sleep 0.2; done
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
plasma)
    check 'Plasma test packages install' sudo dnf -y install --skip-unavailable plasma-workspace plasma-workspace-wayland kwin dolphin \
        konsole wl-clipboard weston xorg-x11-server-Xorg xorg-x11-xauth xrandr xdotool ImageMagick dbus-tools pulseaudio-utils
    # The cloud kernel omits audio drivers. Give this nested desktop a real
    # PipeWire test sink so its startup sound can complete without hardware.
    systemctl --user start pipewire-pulse.socket wireplumber.service
    pactl load-module module-null-sink sink_name=vigil_test >"$OUT/audio-sink.log" || exit 1
    LOG=$OUT/plasma-fake-vigil.log
    export VIGIL_ASK_SERVER=http://127.0.0.1:8765
    python3 -B "$M/source/vigil-ask/tests/fake-vigil.py" 8765 "$LOG" slow >"$OUT/plasma-fake-vigil.out" 2>&1 &
    FAKE_SERVER=$!
    mkdir -p ~/.config/plasma-workspace/env
    printf 'export VIGIL_ASK_SERVER=%s\n' "$VIGIL_ASK_SERVER" >~/.config/plasma-workspace/env/vigil-ask-test.sh
    for _ in {1..50}; do curl -sf "$VIGIL_ASK_SERVER/login" >/dev/null && break; sleep 0.2; done
    installed 'from vigil_ask import core, vigil_glm; core.save_config(notice_accepted=True)
vigil_glm.save_session({"access_token": "fake-access-1", "refresh_token": "fake-refresh-1", "expires_in": 3600}, "tester@example.invalid")'
    printf 'Notes about VIGIL OS.\n' >~/notes.txt
    export DISPLAY=:99
    touch "$HOME/.Xauthority"
    chmod 600 "$HOME/.Xauthority"
    xauth add :99 . "$(mcookie)"
    sudo Xorg :99 -noreset -nolisten tcp -auth "$HOME/.Xauthority" vt7 >"$OUT/plasma-xorg.log" 2>&1 </dev/null &
    XORG=$!
    for _ in {1..150}; do xrandr --query >/dev/null 2>&1 && break; sleep 0.2; done
    xrandr --output Virtual-1 --mode 1920x1080 || exit 1
    # KWin 6.8 requires DMA-BUF and a render device from its Wayland host.
    # Xorg on the VM's virgl GPU provides DRI3; Xvfb cannot supply it.
    weston --backend=x11 --renderer=gl --shell=desktop-shell.so --width=1920 --height=1080 \
        --socket=wayland-test-host --idle-time=0 >"$OUT/weston.log" 2>&1 </dev/null &
    WESTON=$!
    for _ in {1..100}; do [[ -S "$XDG_RUNTIME_DIR/wayland-test-host" ]] && break; sleep 0.2; done
    [[ -S "$XDG_RUNTIME_DIR/wayland-test-host" ]] || { echo 'FAIL: Weston test host did not start'; exit 1; }
    WAYLAND_DISPLAY=wayland-test-host startplasma-wayland >"$OUT/plasma.log" 2>&1 </dev/null &
    owned() { gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus --method org.freedesktop.DBus.NameHasOwner "$1" | grep -q true; }
    for _ in {1..120}; do owned org.kde.plasmashell && owned org.kde.kglobalaccel && break; sleep 0.5; done
    owned org.kde.plasmashell && owned org.kde.kglobalaccel || { echo 'FAIL: nested Plasma did not start'; exit 1; }
    sleep 8
    pkill -u "$USER" -x plasma-welcome
    xdotool mousemove 512 384
    plasma() { python3 -B "$M/source/vigil-ask/tests/vm-plasma.py" "$@"; }
    shot() { import -window root -crop 1024x768+0+0 "$OUT/plasma-$1.png"; }
    asked() { for _ in {1..40}; do grep -q "$1" "$LOG" 2>/dev/null && return 0; sleep 0.5; done; return 1; }
    window_pid() { pgrep -u "$USER" -f '^/usr/bin/python3 -I /usr/bin/vigil-ask window'; }
    check 'Meta+Alt+A and Meta+Alt+Shift+A belong to VIGIL Ask alone' plasma shortcuts
    xdotool key super+alt+a
    check 'Meta+Alt+A opens one VIGIL Ask window' plasma windows 1
    shot shortcut
    xdotool key Escape
    check 'Escape closes it' plasma windows 0
    # KWin picks its own socket name (wayland-1 in 6.8); select text in that session.
    session_wayland=$(tr '\0' '\n' </proc/"$(pgrep -u "$USER" -x plasmashell)"/environ | sed -n 's/^WAYLAND_DISPLAY=//p')
    printf 'selected words on Wayland' | WAYLAND_DISPLAY=$session_wayland wl-copy --primary >/dev/null 2>&1
    for _ in {1..25}; do [[ $(WAYLAND_DISPLAY=$session_wayland wl-paste --primary --no-newline 2>/dev/null) == 'selected words on Wayland' ]] && break; sleep 0.2; done
    xdotool key super+alt+shift+a
    check 'Meta+Alt+Shift+A opens the window' plasma windows 1
    sleep 2
    xdotool type --delay 40 'what is this'
    xdotool key Return
    check 'the Wayland selection goes with the question' asked 'what is this\\n\\n.*selected words on Wayland'
    shot selection
    xdotool key Escape
    plasma windows 0 >/dev/null
    nohup dbus-monitor --session interface=org.kde.krunner1 >"$OUT/plasma-krunner-calls.log" 2>&1 </dev/null &
    MONITOR=$!
    sleep 1
    gdbus call --session --dest org.kde.krunner --object-path /App --method org.kde.krunner.App.query konsole >/dev/null
    sleep 4
    gdbus call --session --dest org.kde.krunner --object-path /App --method org.kde.krunner.App.query 'ask What is KDE Plasma?' >/dev/null
    sleep 5
    shot krunner
    xdotool key Return
    check 'KRunner asks the question in the window' asked 'What is KDE Plasma?'
    kill "$MONITOR"
    check 'KRunner sends VIGIL Ask only queries that start with ask' python3 -I -c 'import re, sys
calls = re.findall(r"destination=(\S+) .*member=Match\n\s+string \"([^\"]*)\"", open(sys.argv[1]).read())
ours = [query for name, query in calls if name == "org.vigilos.Ask.KRunner"]
print(calls); sys.exit(ours != ["ask What is KDE Plasma?"] or not any(q == "konsole" for _, q in calls))' "$OUT/plasma-krunner-calls.log"
    check 'D-Bus starts the runner, and the window gets its own app scope' bash -c \
        'grep -q "/dbus-.*org.vigilos.Ask.KRunner@.*\.service$" /proc/$(pgrep -u "$USER" -f "^/usr/bin/python3 -I /usr/bin/vigil-ask krunner")/cgroup &&
         grep -q "/app-org.vigilos.Ask-.*\.scope$" /proc/$(pgrep -u "$USER" -f "^/usr/bin/python3 -I /usr/bin/vigil-ask window")/cgroup'
    shot krunner-answer
    pkill -u "$USER" -f '^/usr/bin/python3 -I /usr/bin/vigil-ask krunner'
    sleep 2
    check 'the window outlives the runner' plasma windows 1
    xdotool key Escape
    plasma windows 0 >/dev/null
    systemd-run --user --quiet --collect --unit=vigil-ask-test-dolphin dolphin --select "$HOME/notes.txt"
    sleep 8
    xdotool key Menu
    sleep 2
    for _ in {1..8}; do xdotool key Down; sleep 0.2; done
    sleep 1
    shot dolphin-menu
    xdotool key Return
    check 'Dolphin asks VIGIL about the file' bash -c 'for _ in {1..30}; do pgrep -u "$USER" -fx "/usr/bin/python3 -I /usr/bin/vigil-ask window --file $HOME/notes.txt" && exit 0; sleep 0.5; done; exit 1'
    sleep 3
    shot dolphin-file
    systemctl --user stop vigil-ask-test-dolphin.service
    printf 'A question to stop\n' | vigil-ask window --stdin
    check 'a window answer starts' asked 'A question to stop'
    mkdir -p -m 0700 "$HOME/term-run"
    XDG_RUNTIME_DIR=$HOME/term-run vigil-ask ask 'A terminal question' \
        >"$OUT/plasma-terminal-ask.log" 2>&1 </dev/null &
    TERMINAL_ASK=$!
    asked 'A terminal question'
    sleep 1
    gdbus call --session --dest org.freedesktop.ScreenSaver --object-path /ScreenSaver --method org.freedesktop.ScreenSaver.Lock >/dev/null
    sleep 6
    shot locked
    wait "$TERMINAL_ASK"
    check 'locking stops the terminal answer' test $? = 130
    check 'locking stops the window answer' bash -c '[[ $(vigil-ask status) == stopped ]]'
    gdbus call --session --dest org.kde.Shutdown --object-path /Shutdown --method org.kde.Shutdown.logout >/dev/null
    sleep 15
    check 'logging out leaves no VIGIL Ask processes or units' bash -c '! pgrep -u "$USER" -f "^/usr/bin/python3 -I /usr/bin/vigil-ask" &&
        [[ -z $(systemctl --user list-units --no-legend "app-org.vigilos*" "dbus-*vigilos*") ]]'
    rm -f ~/.config/plasma-workspace/env/vigil-ask-test.sh
    vigil-ask signout >/dev/null
    installed 'from vigil_ask import core; core.save_config(notice_accepted=False)'
    systemctl --user unset-environment VIGIL_ASK_SERVER
    kill "$FAKE_SERVER" "$WESTON"
    unset VIGIL_ASK_SERVER
    sudo kill "$XORG"
    ;;
live)
    check 'status is signin with no session' bash -c '[[ $(vigil-ask status) == signin ]]'
    check 'setup shows the cloud notice, then sign-in' installed 'from vigil_ask import core
first = core.setup_state(); core.save_config(notice_accepted=True); second = core.setup_state(); print(first, second)
sys.exit((first, second) != ("notice", "signin"))'
    check 'real VIGIL GLM ends a connection it never issued, and it is forgotten' python3 -I "$M/source/vigil-ask/tests/vm-live.py" refused
    check 'real VIGIL GLM gives the sign-in dialog a code for the browser' env QT_QPA_PLATFORM=offscreen \
        python3 -I "$M/source/vigil-ask/tests/vm-live.py" code "$OUT/signin-code.png"
    check 'vigil-ask signin shows a real code and stops on Ctrl+C' bash -c 'timeout --preserve-status -s INT 15 vigil-ask signin >"$0" 2>&1
        [[ $? == 130 ]] && grep -q "https://chat.vigilglm.ai/desktop/verify" "$0" && grep -qE "^    [A-Za-z0-9-]{4,32}$" "$0" && cat "$0"' "$OUT/live-signin.log"
    check 'terminal ask points to sign-in' bash -c 'vigil-ask ask hello </dev/null; [[ $? == 2 ]]'
    check 'setup screen renders: sign in' env QT_QPA_PLATFORM=offscreen python3 -I "$M/source/vigil-ask/tests/vm-shot.py" "$OUT/setup-signin.png" signin
    check 'unfinished sign-ins saved nothing' bash -c '[[ ! -e ~/.local/state/vigil-ask/session.json ]]'
    ;;
system)
    check 'SELinux enforcing' bash -c '[[ $(getenforce) == Enforcing ]]'
    check 'no AVC denials' bash -c '! sudo journalctl -b --no-pager | grep -q "avc:  denied" && ! sudo grep -qs denied /var/log/audit/audit.log'
    check 'no failed system or user units' bash -c 'systemctl --failed --no-legend; systemctl --user --failed --no-legend; [[ -z $(systemctl --failed --no-legend) && -z $(systemctl --user --failed --no-legend) ]]'
    journalctl --user -b --no-pager >"$OUT/user-journal.log"
    check 'installed files still verify' rpm -V vigil-ask
    ;;
*) echo "usage: vm-checks.sh package|unit|i3|plasma|live|system" >&2; exit 2 ;;
esac
