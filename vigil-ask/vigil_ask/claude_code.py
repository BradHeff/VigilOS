"""Claude Code as the VIGIL Ask provider: ask, stream, cancel and escalate."""
from __future__ import annotations
import collections, json, queue, shutil, signal, subprocess, threading, urllib.parse
from . import core

NAME = 'Claude Code'
VENDOR = 'Anthropic'
MIN_VERSION = (2, 1, 309)
MAX_LINK_PROMPT = 5000
SIGNIN_HINTS = ('not logged in', 'please run /login', 'log in', 'authentication', 'oauth', 'invalid api key')


def command(claude, model=None, resume=None):
    """No tools, no MCP servers and no user, project or local settings: Quick Ask only answers."""
    argv = [claude, '-p', '--output-format', 'stream-json', '--verbose', '--include-partial-messages',
            '--tools', '', '--strict-mcp-config', '--setting-sources', '', '--permission-mode', 'dontAsk',
            '--settings', str(core.DATA / 'quick-settings.json'),
            '--append-system-prompt', (core.DATA / 'system-prompt.md').read_text()]
    if model:
        argv += ['--model', model]
    if resume:
        argv += ['--resume', resume]
    if shutil.which('setpriv'):
        argv = ['setpriv', '--pdeathsig', 'TERM', '--', *argv]
    return argv


class Stream:
    """Turns stream-json lines into ('session', id), ('text', chunk), ('retry', note) and ('result', outcome)."""

    def __init__(self):
        self.session_id = None
        self.streamed = False
        self.auth_error = False
        self.outcome = None

    def feed(self, line):
        try:
            event = json.loads(line)
        except ValueError:
            return []
        if not isinstance(event, dict):
            return []
        kind = event.get('type')
        out = []
        if event.get('session_id') and event['session_id'] != self.session_id:
            self.session_id = event['session_id']
            out.append(('session', self.session_id))
        if kind == 'stream_event':
            inner = event.get('event') or {}
            if inner.get('type') == 'message_start':
                self.streamed = False
            delta = inner.get('delta') or {}
            if delta.get('type') == 'text_delta' and delta.get('text'):
                self.streamed = True
                out.append(('text', delta['text']))
        elif kind == 'assistant':
            message = event.get('message') or {}
            if event.get('error') == 'authentication_failed':
                self.auth_error = True
            elif not self.streamed:
                text = ''.join(b.get('text', '') for b in message.get('content') or [] if b.get('type') == 'text')
                if text:
                    out.append(('text', text))
            self.streamed = False
        elif kind == 'system' and event.get('subtype') == 'api_retry':
            out.append(('retry', f'Retrying ({event.get("error", "error")}, attempt {event.get("attempt", "?")})'))
        elif kind == 'result':
            self.outcome = self.classify(event)
            out.append(('result', self.outcome))
        return out

    def classify(self, event):
        message = str(event.get('result') or event.get('subtype') or 'Claude Code reported an error.')
        if not event.get('is_error') and event.get('subtype') == 'success':
            return {'state': 'done', 'session_id': self.session_id, 'error': ''}
        signin = self.auth_error or event.get('api_error_status') in (401, 403) or any(h in message.lower() for h in SIGNIN_HINTS)
        return {'state': 'signin' if signin else 'failed', 'session_id': self.session_id, 'error': message[:500]}


class Run:
    """One turn in a child process. Events arrive on .events; the last is ('end', outcome)."""

    def __init__(self, claude, payload, model=None, resume=None):
        self.events = queue.Queue()
        self.stream = Stream()
        self.cancelled = False
        self.errors = collections.deque(maxlen=12)
        self.process = subprocess.Popen(command(claude, model, resume), cwd=core.work_dir(), stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for target, arg in ((self._write, payload.encode()), (self._drain, None), (self._read, None)):
            threading.Thread(target=target, args=(arg,) if arg is not None else (), daemon=True).start()

    def _write(self, data):
        try:
            self.process.stdin.write(data)
            self.process.stdin.close()
        except OSError:
            pass

    def _drain(self):
        with self.process.stderr:
            for line in self.process.stderr:
                self.errors.append(line.decode(errors='replace').rstrip())

    def _read(self):
        with self.process.stdout:
            for line in self.process.stdout:
                for event in self.stream.feed(line):
                    self.events.put(event)
        code = self.process.wait()
        if self.stream.outcome and self.stream.outcome['state'] == 'done':
            outcome = self.stream.outcome
        elif self.cancelled:
            outcome = {'state': 'stopped', 'session_id': self.stream.session_id, 'error': ''}
        elif self.stream.outcome:
            outcome = self.stream.outcome
        else:
            detail = next((e for e in reversed(self.errors) if e.strip()), f'Claude Code exited with status {code}.')
            outcome = {'state': 'failed', 'session_id': self.stream.session_id, 'error': detail[:500]}
        self.events.put(('end', outcome))

    def cancel(self, send=True):
        """SIGINT ends the turn cleanly; escalate only if Claude Code doesn't exit."""
        self.cancelled = True
        if self.process.poll() is not None:
            return
        if send:
            self.process.send_signal(signal.SIGINT)
        def escalate(sig):
            if self.process.poll() is None:
                self.process.send_signal(sig)
        for delay, sig in ((5, signal.SIGTERM), (10, signal.SIGKILL)):
            timer = threading.Timer(delay, escalate, (sig,))
            timer.daemon = True
            timer.start()

    def running(self):
        return self.process.poll() is None


def deep_link(folder, question):
    """Opens an interactive session in folder with the question typed in but not sent."""
    query = urllib.parse.urlencode({'cwd': str(folder), 'q': question[:MAX_LINK_PROMPT]}, quote_via=urllib.parse.quote)
    return f'claude-cli://open?{query}'


def link_handler_registered():
    """Claude Code registers claude-cli:// itself after the first interactive prompt."""
    if not shutil.which('xdg-mime'):
        return False
    result = subprocess.run(['xdg-mime', 'query', 'default', 'x-scheme-handler/claude-cli'],
                            capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return result.returncode == 0 and bool(result.stdout.strip())
