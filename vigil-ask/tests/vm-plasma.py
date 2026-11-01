"""Plasma session checks for the VIGIL Ask test VM: shortcuts, windows and the KRunner runner, over D-Bus."""
import sys, time
import gi
gi.require_version('Gio', '2.0')
from gi.repository import Gio, GLib

bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
META, SHIFT, ALT, CTRL = 0x10000000, 0x02000000, 0x08000000, 0x04000000
WANTED = {META | ALT | ord('A'): '_launch', META | ALT | SHIFT | ord('A'): 'selection'}


def call(name, path, interface, method, args=None, timeout=10000):
    return bus.call_sync(name, path, interface, method, args, None, Gio.DBusCallFlags.NONE, timeout, None).unpack()


def shortcuts():
    """Every active global shortcut key, with the component and action that hold it."""
    held = {}
    for path in call('org.kde.kglobalaccel', '/kglobalaccel', 'org.kde.KGlobalAccel', 'allComponents')[0]:
        for action, _, component, *_, keys, _defaults in call('org.kde.kglobalaccel', path, 'org.kde.kglobalaccel.Component',
                                                              'allShortcutInfos')[0]:
            for key in filter(None, keys):
                held.setdefault(key, []).append((component, action))
    return held


def check_shortcuts():
    deadline = time.monotonic() + 30
    while True:
        held = shortcuts()
        ours = {key: held.get(key, []) for key in WANTED}
        loaded = {component for owners in held.values() for component, _ in owners}
        if {'kwin', 'plasmashell', 'org.vigilos.Ask.desktop'} <= loaded or time.monotonic() > deadline:
            break
        time.sleep(1)
    print(ours)
    return all(owners == [('org.vigilos.Ask.desktop', action)] for (key, action), owners in
               zip(WANTED.items(), ours.values()))


def windows(title='VIGIL Ask'):
    """Open windows whose caption matches, from KWin's own KRunner interface."""
    return [m for m in call('org.kde.KWin', '/WindowsRunner', 'org.kde.krunner1', 'Match', GLib.Variant('(s)', (title,)))[0]
            if m[1] == title]


def wait_windows(count, timeout=30):
    deadline = time.monotonic() + timeout
    while len(found := windows()) != count and time.monotonic() < deadline:
        time.sleep(0.5)
    print(found)
    return len(found) == count


if __name__ == '__main__':
    command = sys.argv[1]
    if command == 'shortcuts':
        sys.exit(not check_shortcuts())
    if command == 'windows':
        sys.exit(not wait_windows(int(sys.argv[2])))
    sys.exit(2)
