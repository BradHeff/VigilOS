"""Answers "ask <question>" typed into KRunner, over the org.kde.krunner1 D-Bus interface."""
from __future__ import annotations
import os, re, shutil, subprocess, sys, uuid
import gi
gi.require_version('Gio', '2.0')
from gi.repository import Gio, GLib
from . import core

NAME = 'org.vigilos.Ask.KRunner'
PATH = '/runner'
TRIGGER = r'(?i)^\s*ask\s+(\S.*)'
IDLE_SECONDS = 600
FORGET_SECONDS = 30
SUBTEXT = {'signin': 'Sign in to VIGIL GLM first'}
INTERFACE = Gio.DBusNodeInfo.new_for_xml('''<node><interface name="org.kde.krunner1">
  <method name="Teardown"/>
  <method name="Config"><arg type="a{sv}" direction="out"/></method>
  <method name="Actions"><arg type="a(sss)" direction="out"/></method>
  <method name="SetActivationToken"><arg type="s" direction="in"/></method>
  <method name="Run"><arg type="s" direction="in"/><arg type="s" direction="in"/></method>
  <method name="Match"><arg type="s" direction="in"/><arg type="a(sssida{sv})" direction="out"/></method>
</interface></node>''').interfaces[0]


def question_in(query):
    found = re.match(TRIGGER, query, re.DOTALL)
    return found.group(1).strip() if found else None


class Runner:
    """Holds only the question last matched, until Run uses it or soon after KRunner closes, which comes before Run."""

    def __init__(self, loop):
        self.loop = loop
        self.question = self.token = self.idle = self.forget = None
        self.children = []
        self.in_session = False
        self.touch()

    def touch(self):
        if self.idle:
            GLib.source_remove(self.idle)
        self.idle = GLib.timeout_add_seconds(IDLE_SECONDS, self.loop.quit)
        self.children = [c for c in self.children if c.poll() is None]

    def call(self, connection, sender, path, interface, method, parameters, invocation):
        self.touch()
        try:
            args = parameters.unpack()
            reply = None
            if method == 'Config':
                reply = GLib.Variant('(a{sv})', ({'MatchRegex': GLib.Variant('s', TRIGGER), 'MinLetterCount': GLib.Variant('i', 5)},))
            elif method == 'Actions':
                reply = GLib.Variant('(a(sss))', ([],))
            elif method == 'Match':
                reply = GLib.Variant('(a(sssida{sv}))', (self.match(args[0]),))
            elif method == 'SetActivationToken':
                self.token = args[0]
            elif method == 'Run':
                self.run()
            elif method == 'Teardown':
                self.forget = self.forget or GLib.timeout_add_seconds(FORGET_SECONDS, self.clear)
            invocation.return_value(reply)
        except Exception as exc:
            invocation.return_dbus_error('org.vigilos.Ask.Error', str(exc))

    def match(self, query):
        question = question_in(query)
        state = core.current_status() if question else 'off'
        if state == 'off':
            return []
        self.clear()
        self.question = question
        properties = {'subtext': GLib.Variant('s', SUBTEXT.get(state, 'Sends the question to VIGIL GLM')),
                      'category': GLib.Variant('s', 'VIGIL Ask'), 'actions': GLib.Variant('as', [])}
        return [('ask', question, 'org.vigilos.Ask', 100, 1.0, properties)]

    def run(self):
        """Hand the question to the window in its own app scope, so it outlives this D-Bus-started service."""
        question, token = self.question, self.token
        self.clear()
        if not question:
            return
        env = {k: v for k, v in os.environ.items() if k not in ('XDG_ACTIVATION_TOKEN', 'INVOCATION_ID')}
        if token:
            env['XDG_ACTIVATION_TOKEN'] = token
        argv = [os.path.abspath(sys.argv[0]), 'window', '--stdin']
        if os.environ.get('INVOCATION_ID') and shutil.which('systemd-run'):
            argv = ['systemd-run', '--user', '--scope', '--quiet', '--collect', '--slice=app.slice',
                    f'--unit=app-org.vigilos.Ask-{uuid.uuid4().hex[:12]}.scope', '--', *argv]
        child = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 env=env, start_new_session=True)
        child.stdin.write(question.encode())
        child.stdin.close()
        self.children.append(child)

    def clear(self):
        if self.forget:
            GLib.source_remove(self.forget)
        self.question = self.token = self.forget = None
        return False

    def session(self, appeared):
        """Leave with the Plasma session, so a later login never reaches a runner holding the old one's environment."""
        if appeared:
            self.in_session = True
        elif self.in_session:
            self.loop.quit()


def main():
    loop = GLib.MainLoop()
    runner = Runner(loop)
    registered = lambda connection, name: connection.register_object(PATH, INTERFACE, runner.call, None, None)
    Gio.bus_own_name(Gio.BusType.SESSION, NAME, Gio.BusNameOwnerFlags.NONE, registered, None, lambda *_: loop.quit())
    Gio.bus_watch_name(Gio.BusType.SESSION, 'org.kde.KWin', Gio.BusNameWatcherFlags.NONE,
                       lambda *_: runner.session(True), lambda *_: runner.session(False))
    loop.run()
    return 0
