#!/usr/bin/python3
"""VIGIL Ask tests against a fake VIGIL GLM server. The window tests run only where PySide6 is installed."""
from unittest.mock import patch
import contextlib, importlib.util, io, json, os, re, shutil, signal, socket, stat, subprocess, sys, tempfile, threading, time, unittest
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from vigil_ask import cli, core, vigil_glm

spec = importlib.util.spec_from_file_location('fake_vigil', HERE / 'fake-vigil.py')
fake_vigil = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_vigil)
MARKER = 'question-marker-7f3a'
ANSWER = 'Fake answer for tests.'


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='vigil-ask-test-')
        self.t = Path(self.tmp.name)
        (self.t / 'run').mkdir(mode=0o700)
        self.fake = fake_vigil.Fake(log=self.t / 'fake.log').start()
        env = {'XDG_CONFIG_HOME': self.t / 'config', 'XDG_STATE_HOME': self.t / 'state', 'XDG_RUNTIME_DIR': self.t / 'run',
               'XDG_DATA_HOME': self.t / 'data', 'XDG_CACHE_HOME': self.t / 'cache', 'VIGIL_ASK_SERVER': self.fake.url}
        self.saved = {k: os.environ.get(k) for k in env}
        os.environ.update({k: str(v) for k, v in env.items()})
        self.admin, core.ADMIN_OFF = core.ADMIN_OFF, self.t / 'admin-off'

    def tearDown(self):
        core.ADMIN_OFF = self.admin
        self.fake.shutdown()
        self.fake.server_close()
        for key, value in self.saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()

    def calls(self):
        return [r for r in self.fake.requests if 'body' in r]

    def finish(self, run, timeout=15):
        events, deadline = [], time.monotonic() + timeout
        while True:
            kind, value = run.events.get(timeout=max(0.1, deadline - time.monotonic()))
            events.append((kind, value))
            if kind == 'end':
                return events

    def ask(self, question='q', turns=()):
        return vigil_glm.Run(vigil_glm.conversation(turns, core.compose(question)))

    def sign_in(self):
        return vigil_glm.save_session(fake_vigil.TOKENS, fake_vigil.EMAIL)

    def paths(self, path):
        return [r for r in self.fake.requests if r['path'] == path and 'disconnected' not in r]

    def ready(self):
        core.save_config(notice_accepted=True)
        self.sign_in()


class Session(Base):
    def test_the_session_goes_only_to_its_own_server(self):
        self.sign_in()
        path = vigil_glm.session_path()
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
        self.assertEqual(vigil_glm.load_session()['email'], fake_vigil.EMAIL)
        os.environ['VIGIL_ASK_SERVER'] = 'http://127.0.0.1:1'
        self.assertIsNone(vigil_glm.load_session(), 'a session is kept only for the server it came from')
        for elsewhere in ('https://example.com', 'http://127.0.0.1.example.com', 'http://user:pw@127.0.0.1', 'http://127.0.0.1/api', 'file:///tmp'):
            os.environ['VIGIL_ASK_SERVER'] = elsewhere
            with self.assertRaises(ValueError, msg=elsewhere):
                vigil_glm.origin()
        del os.environ['VIGIL_ASK_SERVER']
        self.assertEqual(vigil_glm.origin(), 'https://chat.vigilglm.ai')

    def test_only_well_formed_tokens_are_kept(self):
        for change in ({'refresh_token': None}, {'access_token': 'a b'}, {'access_token': 'a\r\nX: y'}, {'token_type': 'mac'},
                       {'expires_in': 0}, {'expires_in': '3600'}, {'access_token': 'x' * 5000}):
            with self.assertRaises(ValueError, msg=change):
                vigil_glm.save_session({**fake_vigil.TOKENS, **change})
        self.assertIsNone(vigil_glm.load_session())
        record = self.sign_in()
        self.assertEqual((record['access_token'], record['email']), (fake_vigil.TOKENS['access_token'], fake_vigil.EMAIL))
        self.assertAlmostEqual(record['expires'], time.time() + 3600, delta=5)

    def test_malformed_sessions_and_old_web_sessions_are_signed_out(self):
        good = self.sign_in()
        for change in ({'access_token': 42}, {'refresh_token': ['x']}, {'expires': '1'}, {'email': None}, {'id': 7}):
            core.write_private(vigil_glm.session_path(), json.dumps({**good, **change}))
            self.assertIsNone(vigil_glm.load_session(), change)
        core.write_private(vigil_glm.session_path(), json.dumps({'cookie': 'vigil_session=web', 'origin': self.fake.url, 'email': ''}))
        self.assertIsNone(vigil_glm.load_session())
        self.assertFalse(vigil_glm.session_path().exists(), 'a web session from an earlier VIGIL Ask is deleted')

    def test_account_usage_and_sign_out(self):
        session = self.sign_in()
        self.assertEqual(vigil_glm.account(session)['email'], fake_vigil.EMAIL)
        self.assertEqual(vigil_glm.usage(session), 'Used 12% of the 5-hour limit and 3% of the weekly limit')
        stranger = vigil_glm.session_record({**fake_vigil.TOKENS, 'access_token': 'never-issued', 'refresh_token': 'never-issued'})
        with self.assertRaises(vigil_glm.SignedOut):
            vigil_glm.account(stranger)
        self.assertEqual(vigil_glm.usage(stranger), '')
        self.assertEqual(vigil_glm.load_session(), session, 'a stranger turned away leaves the saved connection alone')
        self.assertIn('limit reached', vigil_glm.usage_line({**fake_vigil.USAGE, 'capped': {'window': 'week'}}))
        self.assertEqual(vigil_glm.usage_line({'percent': 'x'}), '')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(cli.main(['signout']), 0)
        self.assertIn('disconnected', out.getvalue())
        self.assertFalse(vigil_glm.session_path().exists())
        self.assertIn('desktop-1', self.fake.revoked, 'VIGIL GLM ends the connection too')

    def test_sign_out_when_vigil_glm_is_unreachable(self):
        self.sign_in()
        self.fake.shutdown()
        self.fake.server_close()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(cli.main(['signout']), 0)
        self.assertIn('Connected desktops', out.getvalue())
        self.assertIsNone(vigil_glm.load_session(), 'the tokens leave this computer anyway')
        self.fake = fake_vigil.Fake().start()


class Renewal(Base):
    def test_an_expired_access_token_is_renewed_and_the_question_still_goes(self):
        self.sign_in()
        self.fake.expire_access()
        events = self.finish(self.ask(MARKER))
        self.assertEqual(events[-1][1]['state'], 'done')
        first, second = [c['headers']['authorization'] for c in self.calls()]
        self.assertEqual(first, 'Bearer fake-access-1')
        renewed = vigil_glm.load_session()
        self.assertEqual(second, f'Bearer {renewed["access_token"]}')
        self.assertNotEqual(renewed['refresh_token'], fake_vigil.TOKENS['refresh_token'])
        self.assertEqual(len(self.paths('/api/desktop/token/refresh')), 1)

    def test_due_tokens_are_renewed_once_for_every_process(self):
        session = self.sign_in()
        session = vigil_glm.store({**session, 'expires': int(time.time()) + 10})
        renewed = []
        threads = [threading.Thread(target=lambda: renewed.append(vigil_glm.fresh(session))) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(10)
        self.assertEqual(len({r['access_token'] for r in renewed}), 1)
        self.assertEqual(len(self.paths('/api/desktop/token/refresh')), 1, 'a refresh token is used once only')
        self.assertEqual(vigil_glm.account(vigil_glm.load_session())['email'], fake_vigil.EMAIL)
        self.assertEqual(self.fake.revoked, set())

    def test_a_revoked_connection_signs_out(self):
        session = self.sign_in()
        self.fake.revoked.add('desktop-1')
        self.assertEqual(vigil_glm.usage(session), '')
        self.assertIsNone(vigil_glm.load_session())


class Device(Base):
    def signin(self):
        process = subprocess.Popen([ROOT / 'vigil-ask', 'signin'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        shown = ''
        while 'Waiting' not in shown:
            line = process.stdout.readline()
            if not line:
                self.fail(process.stderr.read())
            shown += line
        return process, shown

    def test_terminal_sign_in_with_a_browser_code(self):
        process, shown = self.signin()
        self.assertIn(self.fake.url + '/desktop/verify', shown)
        self.assertIn('TEST-0001', shown)
        self.assertIsNone(vigil_glm.load_session())
        self.fake.decide('approve')
        out, err = process.communicate(timeout=15)
        self.assertEqual(process.returncode, 0, err)
        self.assertIn(f'Signed in to VIGIL GLM as {fake_vigil.EMAIL}', out)
        session = vigil_glm.load_session()
        self.assertEqual(session['email'], fake_vigil.EMAIL)
        self.assertEqual(vigil_glm.account(session)['email'], fake_vigil.EMAIL)

    def test_declined_expired_and_cancelled_sign_ins_save_nothing(self):
        for decision, code, words in (('deny', 1, 'declined'), ('expire', 1, 'expired')):
            process, _ = self.signin()
            self.fake.decide(decision)
            out, err = process.communicate(timeout=15)
            self.assertEqual(process.returncode, code, err)
            self.assertIn(words, err)
        process, _ = self.signin()
        process.send_signal(signal.SIGINT)
        out, err = process.communicate(timeout=15)
        self.assertEqual(process.returncode, 130, err)
        self.assertIsNone(vigil_glm.load_session())

    def test_a_grant_from_another_server_is_refused(self):
        def authorize(method, path, session=None, body=None, timeout=15):
            grant = {'protocol_version': 1, 'device_code': 'd' * 43, 'user_code': 'ABCD-1234', 'expires_in': 600, 'interval': 1,
                     'verification_uri': 'https://evil.example/desktop/verify'}
            return 200, grant
        with patch.object(vigil_glm, 'call', authorize):
            flow = vigil_glm.Connect()
            self.assertEqual(flow.events.get(timeout=5), ('end', {'state': 'failed', 'email': '',
                             'error': 'VIGIL GLM sent a sign-in code VIGIL Ask does not understand.'}))
        with patch.object(vigil_glm, 'call', lambda *a, **k: (200, {'protocol_version': 2})):
            flow = vigil_glm.Connect()
            self.assertIn('Update VIGIL OS', flow.events.get(timeout=5)[1]['error'])


class Request(Base):
    def test_question_is_sent_without_tools_under_the_account(self):
        self.sign_in()
        self.finish(self.ask(MARKER))
        call = self.calls()[0]
        body, headers = call['body'], call['headers']
        self.assertEqual(headers['authorization'], 'Bearer fake-access-1')
        self.assertNotIn('cookie', headers)
        self.assertEqual(headers['x-vigil-desktop'], 'ask')
        self.assertEqual(headers['accept'], 'text/event-stream')
        self.assertEqual((body['webSearch'], body['imageTool'], body['browserTool']), (False, False, False))
        self.assertEqual((body['model'], body['thinkingEffort']), ('glm-5.3-flash', 'low'))
        self.assertIn('You have no tools in this window', body['messages'][0]['content'])
        self.assertEqual(body['messages'][1], {'role': 'assistant', 'content': vigil_glm.ACK})
        self.assertEqual(body['messages'][-1]['role'], 'user')
        self.assertIn(MARKER, body['messages'][-1]['content'])

    def test_follow_up_sends_the_conversation_so_far(self):
        self.sign_in()
        self.finish(self.ask('second', [('first', 'one')]))
        messages = self.calls()[0]['body']['messages'][2:]
        self.assertEqual([(m['role'], m['content'].strip()) for m in messages],
                         [('user', 'first'), ('assistant', 'one'), ('user', 'second')])
        with self.assertRaises(core.ContextError):
            vigil_glm.conversation([('q', 'a' * core.MAX_REQUEST_BYTES)], 'more')

    def test_model_and_effort_come_from_settings_when_known(self):
        self.sign_in()
        self.finish(vigil_glm.Run(vigil_glm.conversation([], 'q'), 'glm-5.3', 'high'))
        self.finish(vigil_glm.Run(vigil_glm.conversation([], 'q'), 'other-model', 'extreme'))
        bodies = [c['body'] for c in self.calls()]
        self.assertEqual([(b['model'], b['thinkingEffort']) for b in bodies], [('glm-5.3', 'high'), ('glm-5.3-flash', 'low')])


class Streaming(Base):
    def setUp(self):
        super().setUp()
        self.sign_in()

    def test_truncated_stream_is_not_a_completed_answer(self):
        self.fake.mode = 'truncated'
        events = self.finish(self.ask())
        self.assertTrue(any(k == 'text' for k, _ in events))
        self.assertEqual(events[-1][1]['state'], 'failed')
        self.assertIn('before completing', events[-1][1]['error'])

    def test_old_refusal_does_not_delete_a_new_signin(self):
        old = vigil_glm.load_session()
        vigil_glm.save_session(self.fake.issue('desktop-2'), 'new@example.invalid')
        self.fake.mode = 'auth'
        with patch('threading.Thread.start'):
            run = vigil_glm.Run([])
        run._run([], None, None, old)
        self.assertEqual(run.events.get_nowait()[1]['state'], 'signin')
        self.assertEqual(vigil_glm.load_session()['email'], 'new@example.invalid')

    def test_stop_closes_a_connection_owned_by_the_response(self):
        self.fake.mode = 'stalled'
        run = self.ask()
        while run.events.get(timeout=10)[0] != 'text':
            pass
        # HTTPConnection detaches sock for Connection: close responses.
        self.assertIsNone(run.connection.sock)
        run.cancel()
        self.assertEqual(self.finish(run, timeout=3)[-1][1]['state'], 'stopped')
        self.assertTrue(self.fake.disconnected.wait(8))

    def test_answer_streams_after_thinking(self):
        events = self.finish(self.ask())
        self.assertEqual(events[0], ('thinking', None))
        self.assertEqual(''.join(v for k, v in events if k == 'text'), ANSWER)
        self.assertEqual(events[-1][1], {'state': 'done', 'error': ''})

    def test_a_corrected_answer_replaces_the_text(self):
        self.fake.mode = 'replace'
        self.assertIn(('replace', 'Fixed answer.'), self.finish(self.ask()))

    def test_an_ended_session_asks_for_sign_in_and_is_forgotten(self):
        self.fake.mode = 'auth'
        self.assertEqual(self.finish(self.ask())[-1][1]['state'], 'signin')
        self.assertIsNone(vigil_glm.load_session())
        self.assertEqual(self.finish(self.ask())[-1][1]['state'], 'signin')
        self.assertEqual(len(self.calls()), 1, 'nothing is sent without a session')

    def test_refusals_keep_the_servers_words(self):
        for mode, error in (('credits', 'Insufficient credits'), ('crash', 'VIGIL GLM answered 500.'), ('error', 'The model failed')):
            self.fake.mode = mode
            self.assertEqual(self.finish(self.ask())[-1][1], {'state': 'failed', 'error': error}, mode)

    def test_a_usage_limit_is_explained(self):
        self.fake.mode = 'cap'
        events = self.finish(self.ask())
        self.assertTrue(any(k == 'notice' and 'usage limit' in v for k, v in events), events)
        self.assertEqual(events[-1][1]['state'], 'done')

    def test_stop_closes_the_connection(self):
        self.fake.mode = 'slow'
        run = self.ask()
        while run.events.get(timeout=10)[0] != 'text':
            pass
        started = time.monotonic()
        run.cancel()
        events = self.finish(run)
        self.assertEqual(events[-1][1]['state'], 'stopped')
        self.assertLess(time.monotonic() - started, 2)
        self.assertTrue(self.fake.disconnected.wait(10), 'the server should see the request end')

    def test_unreachable_server_fails_plainly(self):
        with socket.socket() as unused:
            unused.bind(('127.0.0.1', 0))
            os.environ['VIGIL_ASK_SERVER'] = f'http://127.0.0.1:{unused.getsockname()[1]}'
        self.sign_in()
        outcome = self.finish(self.ask())[-1][1]
        self.assertEqual(outcome['state'], 'failed')
        self.assertIn('Could not reach VIGIL GLM', outcome['error'])

    def test_noise_is_ignored(self):
        stream = vigil_glm.Stream()
        for line in ('not json\n', 'data: [1, 2]\n', ': keep-alive\n', 'data: {"choices": "x"}\n', 'event: ping\n'):
            self.assertEqual(stream.feed(line), [], line)
        self.assertEqual(stream.feed('data: [DONE]\n'), [])
        self.assertTrue(stream.done)


class Status(Base):
    def test_status_file_never_holds_the_question(self):
        self.ready()
        self.fake.mode = 'slow'
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
        self.assertEqual(core.current_status(), 'signin')
        self.sign_in()
        self.assertEqual(core.current_status(), 'idle')
        core.write_private(core.runtime_dir() / 'status.json', json.dumps({'state': 'working', 'pid': 2 ** 22 + 1}))
        self.assertEqual(core.current_status(), 'idle')
        core.save_config(enabled=False)
        self.assertEqual(core.current_status(), 'off')
        core.save_config(enabled=True)
        core.ADMIN_OFF.touch()
        self.assertEqual(core.current_status(), 'off')

    def test_follow_ends_with_its_bar(self):
        self.sign_in()
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
        for state, colour in (('working', '#edc652'), ('done', '#1763ef'), ('failed', '#df3448'), ('signin', '#7a7a7a')):
            self.assertIn(colour, cli.polybar_line(state))


class Setup(Base):
    def test_each_state_in_order(self):
        core.ADMIN_OFF.touch()
        self.assertEqual(core.setup_state(), 'admin-off')
        core.ADMIN_OFF.unlink()
        core.save_config(enabled=False)
        self.assertEqual(core.setup_state(), 'off')
        core.save_config(enabled=True)
        self.assertEqual(core.setup_state(), 'notice')
        core.save_config(notice_accepted=True)
        self.assertEqual(core.setup_state(), 'signin')
        self.sign_in()
        self.assertEqual(core.setup_state(), 'ready')
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
            core.compose('q', [{'kind': 'file', 'label': 'x', 'text': 'y' * core.MAX_REQUEST_BYTES}])


class History(Base):
    def test_private_follow_ups_and_retention(self):
        entry = core.record_turn('first', 'one')
        self.assertEqual(core.record_turn('second', 'two', entry), entry)
        self.assertEqual([t['q'] for t in core.find_history(entry)['turns']], ['first', 'second'])
        self.assertEqual(stat.S_IMODE(core.history_path().stat().st_mode), 0o600)
        stored = json.loads(core.history_path().read_text())
        stored[0]['updated'] = int(time.time()) - 31 * 86400
        core.history_path().write_text(json.dumps(stored))
        self.assertEqual(core.load_history(), [])
        core.save_config(history_days=0)
        self.assertIsNone(core.record_turn('q', 'a'))
        self.assertFalse(core.history_path().exists())


class Terminal(Base):
    def launch(self, *args, **kwargs):
        return subprocess.run([ROOT / 'vigil-ask', *args], capture_output=True, text=True, timeout=30, **kwargs)

    def test_ask_streams_and_records(self):
        self.ready()
        result = self.launch('ask', MARKER)
        self.assertEqual((result.returncode, result.stdout), (0, ANSWER + '\n'), result.stderr)
        entry = core.load_history()[0]
        self.assertIn(f'conversation {entry["id"]}', result.stderr)
        self.assertEqual(entry['turns'][0], {'q': MARKER, 'a': ANSWER})
        self.assertIn(MARKER, self.calls()[0]['body']['messages'][-1]['content'])
        result = self.launch('ask', '--resume', entry['id'], 'and then?')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([m['content'].strip() for m in self.calls()[1]['body']['messages'][2:]], [MARKER, ANSWER, 'and then?'])
        self.assertEqual(len(core.find_history(entry['id'])['turns']), 2)
        self.assertEqual(self.launch('ask', '--resume', 'unknown', 'q').returncode, 2)

    def test_notice_comes_first(self):
        self.sign_in()
        result = self.launch('ask', MARKER, stdin=subprocess.DEVNULL)
        self.assertEqual(result.returncode, 2)
        self.assertIn('VIGIL GLM', result.stderr)
        self.assertIn('Z.ai', result.stderr)
        self.assertEqual(self.calls(), [])

    def test_sign_in_comes_from_the_window(self):
        core.save_config(notice_accepted=True)
        result = self.launch('ask', MARKER)
        self.assertEqual(result.returncode, 2)
        self.assertIn('press Sign in', result.stderr)
        self.assertEqual(self.calls(), [])
        self.assertEqual(self.launch('status').stdout, 'signin\n')

    def test_cancel_without_window(self):
        self.sign_in()
        self.assertEqual(self.launch('cancel').returncode, 0)
        self.assertEqual(self.launch('status').stdout, 'idle\n')

    def test_cancel_stops_a_terminal_ask(self):
        self.ready()
        self.fake.mode = 'slow'
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

    def test_window_asks_the_question_from_stdin(self):
        sent, saved, stdin = [], cli.open_window, sys.stdin
        cli.open_window = lambda request: sent.append(request) or 0
        sys.stdin = io.StringIO(f'  {MARKER}\n')
        try:
            self.assertEqual(cli.main(['window', '--stdin']), 0)
        finally:
            cli.open_window, sys.stdin = saved, stdin
        self.assertEqual((sent[0]['prompt'], sent[0]['submit']), (MARKER, True))

    def test_activation_token_goes_to_the_open_window(self):
        sent, saved = [], cli.send_to_window
        cli.send_to_window = lambda request: sent.append(request) or True
        os.environ['XDG_ACTIVATION_TOKEN'] = 'token-1'
        try:
            self.assertEqual(cli.open_window({'action': 'open'}), 0)
        finally:
            cli.send_to_window = saved
            del os.environ['XDG_ACTIVATION_TOKEN']
        self.assertEqual(sent[0]['activation_token'], 'token-1')


def have_session_bus_tools():
    try:
        import gi
        gi.require_version('Gio', '2.0')
        from gi.repository import Gio
    except (ImportError, ValueError):
        return False
    return bool(shutil.which('dbus-daemon'))


@unittest.skipUnless(have_session_bus_tools() or os.environ.get('VIGIL_ASK_REQUIRE_WINDOW'), 'PyGObject or dbus-daemon is missing')
class Plasma(Base):
    """The KRunner runner and the lock watch, each against a private session bus."""

    def setUp(self):
        super().setUp()
        from gi.repository import Gio, GLib
        from vigil_ask import krunner
        self.Gio, self.GLib, self.krunner = Gio, GLib, krunner
        self.saved.update({k: os.environ.pop(k, None) for k in ('DBUS_SESSION_BUS_ADDRESS', 'INVOCATION_ID', 'XDG_ACTIVATION_TOKEN')})
        self.daemon = subprocess.Popen(['dbus-daemon', '--session', '--nofork', '--print-address'], stdout=subprocess.PIPE, text=True)
        os.environ['DBUS_SESSION_BUS_ADDRESS'] = self.daemon.stdout.readline().strip()
        flags = Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION
        self.bus = Gio.DBusConnection.new_for_address_sync(os.environ['DBUS_SESSION_BUS_ADDRESS'], flags, None, None)
        self.children = []

    def tearDown(self):
        for child in self.children:
            if child.poll() is None:
                child.kill()
            child.communicate()
        self.bus.close_sync(None)
        self.daemon.terminate()
        self.daemon.communicate()
        super().tearDown()

    def bus_call(self, name, path, interface, method, args=None):
        return self.bus.call_sync(name, path, interface, method, args, None, self.Gio.DBusCallFlags.NO_AUTO_START, 5000, None).unpack()

    def start(self, *argv):
        child = subprocess.Popen([ROOT / 'vigil-ask', *argv], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.children.append(child)
        return child

    def runner(self):
        self.start('krunner')
        deadline = time.monotonic() + 15
        while not self.bus_call('org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus', 'NameHasOwner',
                                self.GLib.Variant('(s)', (self.krunner.NAME,)))[0]:
            self.assertLess(time.monotonic(), deadline, 'the runner never took its bus name')
            time.sleep(0.05)
        return lambda method, *args: self.bus_call(self.krunner.NAME, self.krunner.PATH, 'org.kde.krunner1', method,
                                                   self.GLib.Variant(f'({"s" * len(args)})', args) if args else None)

    def window_request(self, server, timeout):
        server.settimeout(timeout)
        connection, _ = server.accept()
        with connection:
            line = connection.makefile('rb').readline()
            connection.sendall(b'ok\n')
        return json.loads(line)

    def test_runner_matches_only_ask_queries_and_hands_over_the_question(self):
        self.sign_in()
        call = self.runner()
        config = call('Config')[0]
        self.assertTrue(re.match(config['MatchRegex'], f'ask {MARKER}'))
        self.assertFalse(re.match(config['MatchRegex'], 'firefox'))
        self.assertEqual(call('Match', 'firefox'), ([],))
        (match,), = call('Match', f'ask  {MARKER}')
        self.assertEqual(match[:3], ('ask', MARKER, 'org.vigilos.Ask'))
        self.assertEqual(match[5]['subtext'], 'Sends the question to VIGIL GLM')
        with socket.socket(socket.AF_UNIX) as server:
            server.bind(str(core.runtime_dir() / 'window.sock'))
            server.listen(1)
            call('Teardown')
            call('SetActivationToken', 'token-1')
            call('Run', 'ask', '')
            request = self.window_request(server, 15)
            self.assertEqual((request['prompt'], request['submit'], request['activation_token']), (MARKER, True, 'token-1'))
            call('Run', 'ask', '')
            with self.assertRaises(socket.timeout):
                self.window_request(server, 2)

    def test_runner_points_to_sign_in_and_is_silent_when_turned_off(self):
        call = self.runner()
        self.assertIn('Sign in', call('Match', 'ask anything')[0][0][5]['subtext'])
        core.save_config(enabled=False)
        self.assertEqual(call('Match', 'ask anything'), ([],))

    def test_screen_lock_stops_a_terminal_ask(self):
        self.ready()
        self.fake.mode = 'slow'
        self.assertEqual(self.bus_call('org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus', 'RequestName',
                                       self.GLib.Variant('(su)', ('org.freedesktop.ScreenSaver', 0))), (1,))
        ask = self.start('ask', MARKER)
        deadline = time.monotonic() + 10
        while core.current_status() != 'working':
            self.assertLess(time.monotonic(), deadline, 'status never showed working')
            time.sleep(0.05)
        time.sleep(0.5)
        self.bus.emit_signal(None, '/org/freedesktop/ScreenSaver', 'org.freedesktop.ScreenSaver', 'ActiveChanged',
                             self.GLib.Variant('(b)', (True,)))
        self.bus.flush_sync(None)
        out, err = ask.communicate(timeout=10)
        self.assertEqual(ask.returncode, 130, err)


def have_pyside(module='QtWidgets'):
    try:
        importlib.import_module(f'PySide6.{module}')
        return True
    except ImportError:
        return False


@unittest.skipUnless(have_pyside() or os.environ.get('VIGIL_ASK_REQUIRE_WINDOW'), 'PySide6 is not installed')
class WindowSmoke(Base):
    def setUp(self):
        super().setUp()
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication
        from vigil_ask import window
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
        self.app = QApplication.instance() or QApplication(['vigil-ask-window'])
        self.window = window

    def open(self):
        w = self.window.Window(open(core.runtime_dir() / 'window.lock', 'a'))
        w.show()
        return w

    def until(self, condition, timeout=15):
        deadline = time.monotonic() + timeout
        while not condition():
            self.assertLess(time.monotonic(), deadline)
            self.app.processEvents()
            time.sleep(0.02)

    def test_ask_follow_up_stop_and_socket(self):
        self.ready()
        w = self.open()
        self.assertEqual(w.state, 'ready')
        self.until(lambda: 'Used 12%' in w.account.text())
        self.assertIn(fake_vigil.EMAIL, w.account.text())
        w.apply({'action': 'open', 'prompt': MARKER, 'submit': True, 'context': [core.text_item('selection', 'Selection', 'picked')]})
        self.until(lambda: w.run is None and w.turns and w.turns[-1]['state'] == 'done')
        self.assertIn(ANSWER, w.answer.toPlainText())
        self.assertIn('picked', self.calls()[0]['body']['messages'][-1]['content'])
        self.assertEqual(w.ask_button.text(), 'Follow up')
        shot = os.environ.get('VIGIL_ASK_SCREENSHOT')
        if shot:
            w.grab().save(shot)
        self.fake.mode = 'slow'
        w.prompt.setPlainText('follow-up question')
        w.send()
        self.until(lambda: w.turns[-1]['a'])
        sender = threading.Thread(target=cli.send_to_window, args=({'action': 'cancel'},))
        sender.start()
        self.until(lambda: w.run is None, timeout=8)
        sender.join()
        self.assertEqual(w.turns[-1]['state'], 'stopped')
        follow_up = self.calls()[1]['body']['messages']
        self.assertIn('picked', follow_up[2]['content'], 'the follow-up carries the first turn as it was sent')
        self.assertEqual(follow_up[3]['content'], ANSWER)
        w.close()
        self.assertFalse((core.runtime_dir() / 'status.json').exists())

    def test_close_releases_qt_objects_before_a_usage_worker_finishes(self):
        from PySide6.QtCore import QCoreApplication, QEvent
        from shiboken6 import isValid
        started, release, finished = threading.Event(), threading.Event(), threading.Event()

        def delayed_usage(session):
            started.set()
            release.wait(10)
            finished.set()
            return 'late usage'

        self.ready()
        with patch.object(vigil_glm, 'usage', side_effect=delayed_usage):
            w = self.open()
            try:
                self.until(started.is_set)
                lock = w.lock
                w.close()
                QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
                self.assertFalse(isValid(w), 'Qt objects must be destroyed on the GUI thread at close')
                self.assertTrue(lock.closed, 'the window must release its lock file')
            finally:
                release.set()
                self.until(finished.is_set)

    def test_disable_is_rechecked_before_sending(self):
        self.ready()
        w = self.open()
        core.ADMIN_OFF.touch()
        w.prompt.setPlainText(MARKER)
        w.send()
        self.assertIsNone(w.run)
        self.assertEqual(w.state, 'admin-off')
        self.assertEqual(self.calls(), [])
        w.close()

    def test_signout_cancels_and_ignores_stale_usage(self):
        self.ready()
        w = self.open()
        session = vigil_glm.load_session()
        self.fake.mode = 'slow'
        w.apply({'prompt': MARKER, 'submit': True})
        self.until(lambda: self.calls())
        w.sign_out()
        self.until(lambda: w.run is None)
        w.pending += 1
        w.jobs.put(('usage', session, 'stale usage'))
        w.poll()
        self.assertEqual(w.account.text(), '')
        self.assertEqual(w.state, 'signin')
        self.assertEqual(w.turns, [])
        self.assertIsNone(vigil_glm.load_session())
        self.until(lambda: 'desktop-1' in self.fake.revoked)
        w.close()

    def test_a_closed_sign_in_saves_nothing(self):
        from vigil_ask import signin
        with patch.object(signin, 'QDesktopServices'):
            dialog = signin.SignIn()
            self.until(lambda: dialog.code.text().startswith('TEST-'))
            dialog.reject()
            self.fake.decide('approve')
            time.sleep(2.5)
        self.assertIsNone(vigil_glm.load_session())
        self.assertEqual(len(self.fake.devices), 1, 'no tokens were collected for a closed sign-in')

    def test_ended_session_returns_to_sign_in(self):
        self.ready()
        w = self.open()
        self.fake.mode = 'auth'
        item = core.text_item('file', 'notes.txt', 'keep this context')
        w.apply({'action': 'open', 'prompt': MARKER, 'submit': True, 'context': [item]})
        self.until(lambda: w.run is None and w.state == 'signin')
        self.assertEqual(w.items, [item], 'attachments wait for reauthentication too')
        self.assertEqual(w.prompt.toPlainText(), MARKER, 'the question waits for the next sign-in')
        self.assertTrue(w.signout_button.isHidden())
        w.close()

    def test_sign_in_through_the_browser(self):
        from vigil_ask import signin
        core.save_config(notice_accepted=True)
        w = self.open()
        self.assertEqual((w.state, core.current_status()), ('signin', 'signin'))
        with patch.object(signin, 'QDesktopServices') as desktop:
            w.sign_in()
            dialog = w.signin
            self.until(lambda: dialog.code.text() == 'TEST-0001')
            self.assertEqual(desktop.openUrl.call_args[0][0].toString(), self.fake.url + '/desktop/verify')
            shot = os.environ.get('VIGIL_ASK_CODE_SCREENSHOT')
            if shot:
                dialog.grab().save(shot)
            self.fake.decide('deny')
            self.until(lambda: not dialog.again_button.isHidden())
            self.assertIn('declined', dialog.status.text())
            dialog.again_button.click()
            self.until(lambda: dialog.code.text() == 'TEST-0002')
            self.fake.decide('approve')
            self.until(lambda: w.state == 'ready')
        self.assertFalse(dialog.isVisible())
        self.assertEqual(vigil_glm.load_session()['email'], fake_vigil.EMAIL)
        self.until(lambda: 'Used 12%' in w.account.text())
        shot = os.environ.get('VIGIL_ASK_SIGNIN_SCREENSHOT')
        if shot:
            w.grab().save(shot)
        w.sign_out()
        self.assertEqual((w.state, vigil_glm.load_session()), ('signin', None))
        self.until(lambda: len(self.fake.revoked) == 1)
        w.close()

    def test_terminal_sign_in_reaches_the_open_window(self):
        core.save_config(notice_accepted=True)
        w = self.open()
        self.sign_in()
        sender = threading.Thread(target=cli.send_to_window, args=({'action': 'check'},))
        sender.start()
        self.until(lambda: w.state == 'ready')
        sender.join()
        w.close()


if __name__ == '__main__':
    unittest.main(verbosity=1)
