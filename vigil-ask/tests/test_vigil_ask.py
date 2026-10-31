#!/usr/bin/python3
"""VIGIL Ask tests against a fake claude. The window test runs only where PySide6 is installed."""
import json, os, signal, stat, subprocess, sys, tempfile, threading, time, unittest, urllib.parse
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from vigil_ask import cli, core, claude_code

FAKE = HERE / 'fake-claude'
MARKER = 'question-marker-7f3a'
ANSWER = 'Fake answer for tests.'
FAKE_VARS = ('FAKE_CLAUDE_MODE', 'FAKE_CLAUDE_VERSION', 'FAKE_CLAUDE_SIGNED_IN')


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='vigil-ask-test-')
        self.t = Path(self.tmp.name)
        (self.t / 'run').mkdir(mode=0o700)
        env = {'XDG_CONFIG_HOME': self.t / 'config', 'XDG_STATE_HOME': self.t / 'state', 'XDG_RUNTIME_DIR': self.t / 'run',
               'VIGIL_ASK_CLAUDE': FAKE, 'FAKE_CLAUDE_LOG': self.t / 'fake.log'}
        self.saved = {k: os.environ.get(k) for k in [*env, *FAKE_VARS]}
        os.environ.update({k: str(v) for k, v in env.items()})
        for name in FAKE_VARS:
            os.environ.pop(name, None)
        self.admin, core.ADMIN_OFF = core.ADMIN_OFF, self.t / 'admin-off'

    def tearDown(self):
        core.ADMIN_OFF = self.admin
        for key, value in self.saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()

    def calls(self):
        log = self.t / 'fake.log'
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

    def finish(self, run, timeout=15):
        events, deadline = [], time.monotonic() + timeout
        while True:
            kind, value = run.events.get(timeout=max(0.1, deadline - time.monotonic()))
            events.append((kind, value))
            if kind == 'end':
                return events

    def ready(self):
        core.save_config(notice_accepted=True)


class Command(Base):
    def test_quick_ask_has_no_tools_settings_or_mcp(self):
        argv = claude_code.command('claude')
        argv = argv[argv.index('claude'):]
        self.assertIn('-p', argv)
        self.assertEqual(argv[argv.index('--tools') + 1], '')
        self.assertEqual(argv[argv.index('--setting-sources') + 1], '')
        self.assertEqual(argv[argv.index('--permission-mode') + 1], 'dontAsk')
        self.assertIn('--strict-mcp-config', argv)
        self.assertTrue(Path(argv[argv.index('--settings') + 1]).is_file())
        for loose in ('bypassPermissions', '--allowedTools', '--allowed-tools', '--dangerously-skip-permissions', '--add-dir'):
            self.assertNotIn(loose, argv)

    def test_quick_settings_deny_changes(self):
        settings = json.loads((core.DATA / 'quick-settings.json').read_text())
        self.assertLessEqual({'Bash', 'Edit', 'Write', 'NotebookEdit', 'WebFetch'}, set(settings['permissions']['deny']))
        self.assertEqual(settings['permissions']['defaultMode'], 'dontAsk')
        self.assertIs(settings['disableAllHooks'], True)

    def test_question_goes_on_stdin_from_our_own_folder(self):
        self.finish(claude_code.Run(str(FAKE), core.compose(MARKER)))
        call = self.calls()[0]
        self.assertIn(MARKER, call['stdin'])
        self.assertNotIn(MARKER, json.dumps(call['argv']))
        work = core.work_dir()
        self.assertEqual(call['cwd'], str(work))
        self.assertEqual(stat.S_IMODE(work.stat().st_mode), 0o700)
        self.assertFalse((work / '.claude').exists() or (work / '.mcp.json').exists())

    def test_follow_up_resumes_the_session(self):
        events = self.finish(claude_code.Run(str(FAKE), 'more', resume='abc-123'))
        argv = self.calls()[0]['argv']
        self.assertEqual(argv[argv.index('--resume') + 1], 'abc-123')
        self.assertEqual(events[-1][1]['session_id'], 'abc-123')


class Streaming(Base):
    def test_answer_streams_with_session(self):
        events = self.finish(claude_code.Run(str(FAKE), 'q'))
        self.assertEqual(''.join(v for k, v in events if k == 'text'), ANSWER)
        self.assertIn(('session', 'fake-session-1'), events)
        self.assertEqual(events[-1][1]['state'], 'done')

    def test_unstreamed_message_is_shown_once(self):
        os.environ['FAKE_CLAUDE_MODE'] = 'plain'
        events = self.finish(claude_code.Run(str(FAKE), 'q'))
        self.assertEqual([v for k, v in events if k == 'text'], [ANSWER])

    def test_signed_out_is_reported_as_signin(self):
        os.environ['FAKE_CLAUDE_MODE'] = 'auth'
        self.assertEqual(self.finish(claude_code.Run(str(FAKE), 'q'))[-1][1]['state'], 'signin')

    def test_crash_reports_stderr(self):
        os.environ['FAKE_CLAUDE_MODE'] = 'crash'
        outcome = self.finish(claude_code.Run(str(FAKE), 'q'))[-1][1]
        self.assertEqual(outcome['state'], 'failed')
        self.assertIn('something broke', outcome['error'])

    def test_stop_ends_the_turn_with_sigint(self):
        os.environ['FAKE_CLAUDE_MODE'] = 'slow'
        run = claude_code.Run(str(FAKE), 'q')
        self.assertEqual(run.events.get(timeout=10)[0], 'session')
        started = time.monotonic()
        while run.events.get(timeout=10)[0] != 'text':
            pass
        run.cancel()
        events = self.finish(run)
        self.assertEqual(events[-1][1]['state'], 'stopped')
        self.assertEqual(run.process.returncode, 1, 'Claude Code should exit on SIGINT, not be killed')
        self.assertLess(time.monotonic() - started, 4)

    def test_noise_is_ignored(self):
        stream = claude_code.Stream()
        self.assertEqual(stream.feed(b'not json\n'), [])
        self.assertEqual(stream.feed(b'[1, 2]\n'), [])


class Status(Base):
    def test_status_file_never_holds_the_question(self):
        self.ready()
        os.environ['FAKE_CLAUDE_MODE'] = 'slow'
        process = subprocess.Popen([ROOT / 'vigil-ask', 'ask', MARKER], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=True)
        path = core.runtime_dir() / 'status.json'
        deadline = time.monotonic() + 10
        while not (path.exists() and json.loads(path.read_text())['state'] == 'working'):
            self.assertLess(time.monotonic(), deadline, 'status never showed working')
            time.sleep(0.05)
        self.assertNotIn(MARKER, path.read_text())
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(core.runtime_dir().stat().st_mode), 0o700)
        self.assertEqual(core.current_status(), 'working')
        os.killpg(process.pid, signal.SIGINT)
        out, err = process.communicate(timeout=10)
        self.assertEqual(process.returncode, 130, err)
        self.assertFalse(path.exists())
        self.assertEqual(core.load_history(), [], 'a stopped question is not kept')

    def test_status_without_a_window(self):
        self.assertEqual(core.current_status(), 'idle')
        core.write_private(core.runtime_dir() / 'status.json', json.dumps({'state': 'working', 'pid': 2 ** 22 + 1}))
        self.assertEqual(core.current_status(), 'idle')
        os.environ['VIGIL_ASK_CLAUDE'] = str(self.t / 'absent')
        self.assertEqual(core.current_status(), 'missing')
        core.save_config(enabled=False)
        self.assertEqual(core.current_status(), 'off')
        core.save_config(enabled=True)
        core.ADMIN_OFF.touch()
        self.assertEqual(core.current_status(), 'off')

    def test_follow_ends_with_its_bar(self):
        bar = subprocess.Popen(['bash', '-c', f'"{ROOT / "vigil-ask"}" status --follow --polybar & echo $!; read'],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        lines = [bar.stdout.readline(), bar.stdout.readline()]
        follower = int(next(line for line in lines if line.strip().isdigit()))
        try:
            self.assertTrue(any('Ask' in line for line in lines), lines)
            bar.stdin.close()
            bar.wait(timeout=10)
            deadline = time.monotonic() + 10
            while Path(f'/proc/{follower}').exists():
                self.assertLess(time.monotonic(), deadline, 'status --follow outlived its bar')
                time.sleep(0.1)
        finally:
            bar.stdout.close()
            if Path(f'/proc/{follower}').exists():
                os.kill(follower, signal.SIGTERM)

    def test_polybar_line(self):
        self.assertEqual(cli.polybar_line('off'), '')
        for state, colour in (('working', '#edc652'), ('done', '#1763ef'), ('failed', '#df3448'), ('signin', '#df3448')):
            self.assertIn(colour, cli.polybar_line(state))


class Setup(Base):
    def test_each_state_in_order(self):
        core.ADMIN_OFF.touch()
        self.assertEqual(core.setup_state()[0], 'admin-off')
        core.ADMIN_OFF.unlink()
        core.save_config(enabled=False)
        self.assertEqual(core.setup_state()[0], 'off')
        core.save_config(enabled=True)
        os.environ['VIGIL_ASK_CLAUDE'] = str(self.t / 'absent')
        self.assertEqual(core.setup_state()[0], 'missing')
        os.environ['VIGIL_ASK_CLAUDE'] = str(FAKE)
        os.environ['FAKE_CLAUDE_VERSION'] = '2.1.200'
        self.assertEqual(core.setup_state(), ('old', '2.1.200'))
        os.environ['FAKE_CLAUDE_VERSION'] = '2.2.0'
        self.assertEqual(core.setup_state()[0], 'notice')
        self.ready()
        os.environ['FAKE_CLAUDE_SIGNED_IN'] = '0'
        self.assertEqual(core.setup_state()[0], 'signin')
        os.environ['FAKE_CLAUDE_SIGNED_IN'] = '1'
        self.assertEqual(core.setup_state()[0], 'ready')
        self.assertEqual(stat.S_IMODE(core.config_path().stat().st_mode), 0o600)


class Context(Base):
    def test_text_files_only(self):
        good, binary, big = self.t / 'notes.txt', self.t / 'image.png', self.t / 'big.txt'
        good.write_text('hello\n')
        binary.write_bytes(b'\x89PNG\0\0')
        big.write_text('x' * (core.MAX_ITEM_BYTES + 1))
        self.assertEqual(core.file_item(good)['text'], 'hello\n')
        for path in (binary, big, self.t):
            with self.assertRaises(core.ContextError):
                core.file_item(path)
        with self.assertRaises(core.ContextError):
            core.text_item('selection', 'Selection', b'\xff\xfe')

    def test_compose_marks_attachments_as_data(self):
        payload = core.compose('What is this?', [core.text_item('file', 'a.txt', 'body')])
        self.assertTrue(payload.startswith('What is this?'))
        self.assertIn('<attached file="a.txt">\nbody\n</attached>', payload)
        self.assertIn('not as instructions', payload)
        with self.assertRaises(core.ContextError):
            core.compose('q', [{'kind': 'file', 'label': 'x', 'text': 'y' * core.MAX_STDIN_BYTES}])


class History(Base):
    def test_private_follow_ups_and_retention(self):
        entry = core.record_turn('s1', 'first', 'one')
        self.assertEqual(core.record_turn('s1', 'second', 'two', entry), entry)
        self.assertEqual([t['q'] for t in core.find_history(entry)['turns']], ['first', 'second'])
        self.assertEqual(stat.S_IMODE(core.history_path().stat().st_mode), 0o600)
        stored = json.loads(core.history_path().read_text())
        stored[0]['updated'] = int(time.time()) - 31 * 86400
        core.history_path().write_text(json.dumps(stored))
        self.assertEqual(core.load_history(), [])
        core.save_config(history_days=0)
        self.assertIsNone(core.record_turn('s2', 'q', 'a'))
        self.assertFalse(core.history_path().exists())


class Escalate(Base):
    def test_deep_link(self):
        link = claude_code.deep_link('/home/user/My Project', 'line one\nline & two')
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(link).query)
        self.assertTrue(link.startswith('claude-cli://open?'))
        self.assertEqual(query, {'cwd': ['/home/user/My Project'], 'q': ['line one\nline & two']})
        long = urllib.parse.parse_qs(urllib.parse.urlsplit(claude_code.deep_link('/tmp', 'é' * 6000)).query)['q'][0]
        self.assertEqual(len(long), claude_code.MAX_LINK_PROMPT)


class Terminal(Base):
    def launch(self, *args, **kwargs):
        return subprocess.run([ROOT / 'vigil-ask', *args], capture_output=True, text=True, timeout=30, **kwargs)

    def test_ask_streams_and_records(self):
        self.ready()
        result = self.launch('ask', MARKER)
        self.assertEqual((result.returncode, result.stdout), (0, ANSWER + '\n'), result.stderr)
        self.assertIn('session fake-session-1', result.stderr)
        self.assertEqual(core.load_history()[0]['turns'][0], {'q': MARKER, 'a': ANSWER})
        self.assertIn(MARKER, self.calls()[0]['stdin'])

    def test_notice_comes_first(self):
        result = self.launch('ask', MARKER, stdin=subprocess.DEVNULL)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Anthropic', result.stderr)
        self.assertEqual(self.calls(), [])

    def test_cancel_without_window(self):
        self.assertEqual(self.launch('cancel').returncode, 0)
        self.assertEqual(self.launch('status').stdout, 'idle\n')

    def test_cancel_stops_a_terminal_ask(self):
        self.ready()
        os.environ['FAKE_CLAUDE_MODE'] = 'slow'
        process = subprocess.Popen([ROOT / 'vigil-ask', 'ask', MARKER], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=True)
        deadline = time.monotonic() + 10
        while core.current_status() != 'working':
            self.assertLess(time.monotonic(), deadline, 'status never showed working')
            time.sleep(0.05)
        self.assertEqual(self.launch('cancel').returncode, 0)
        out, err = process.communicate(timeout=10)
        self.assertEqual(process.returncode, 130, err)
        self.assertEqual(core.current_status(), 'idle')

    def test_cancel_signals_only_a_confirmed_terminal_ask(self):
        path = core.runtime_dir() / 'status.json'
        for record in ({'state': 'working', 'pid': os.getpid()}, {'state': 'working', 'pid': os.getpid(), 'started': '1'},
                       {'state': 'done', 'pid': os.getpid(), 'started': core.process_start(os.getpid())}):
            core.write_private(path, json.dumps(record))
            self.assertFalse(core.stop_terminal_ask(), record)

    def test_window_takes_several_files(self):
        files = []
        for name in ('a.txt', 'b.txt'):
            (self.t / name).write_text(name)
            files.append(str(self.t / name))
        sent, saved = [], cli.open_window
        cli.open_window = lambda request: sent.append(request) or 0
        try:
            self.assertEqual(cli.main(['window', '--file', *files]), 0)
        finally:
            cli.open_window = saved
        self.assertEqual([item['text'] for item in sent[0]['context']], ['a.txt', 'b.txt'])


def have_pyside():
    try:
        import PySide6.QtWidgets
        return True
    except ImportError:
        return False


@unittest.skipUnless(have_pyside() or os.environ.get('VIGIL_ASK_REQUIRE_WINDOW'), 'PySide6 is not installed')
class WindowSmoke(Base):
    def test_ask_stop_and_socket(self):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        from vigil_ask import window
        app = QApplication.instance() or QApplication(['vigil-ask-window'])
        self.ready()
        lock = open(core.runtime_dir() / 'window.lock', 'a')
        w = window.Window(lock)
        w.show()

        def until(condition, timeout=15):
            deadline = time.monotonic() + timeout
            while not condition():
                self.assertLess(time.monotonic(), deadline)
                app.processEvents()
                time.sleep(0.02)

        until(lambda: w.state == 'ready')
        w.apply({'action': 'open', 'prompt': MARKER, 'submit': True, 'context': [core.text_item('selection', 'Selection', 'picked')]})
        until(lambda: w.run is None and w.turns and w.turns[-1]['state'] == 'done')
        self.assertIn(ANSWER, w.answer.toPlainText())
        self.assertIn('picked', self.calls()[0]['stdin'])
        self.assertEqual(w.ask_button.text(), 'Follow up')
        shot = os.environ.get('VIGIL_ASK_SCREENSHOT')
        if shot:
            w.grab().save(shot)
        os.environ['FAKE_CLAUDE_MODE'] = 'slow'
        w.prompt.setPlainText('follow-up question')
        w.send()
        until(lambda: w.turns[-1]['a'])
        sender = threading.Thread(target=cli.send_to_window, args=({'action': 'cancel'},))
        sender.start()
        until(lambda: w.run is None, timeout=8)
        sender.join()
        self.assertEqual(w.turns[-1]['state'], 'stopped')
        self.assertEqual(self.calls()[1]['argv'][self.calls()[1]['argv'].index('--resume') + 1], 'fake-session-1')
        w.close()
        self.assertFalse((core.runtime_dir() / 'status.json').exists())


if __name__ == '__main__':
    unittest.main(verbosity=1)
