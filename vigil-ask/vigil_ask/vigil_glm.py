"""VIGIL GLM as the VIGIL Ask provider: connecting this desktop to an account, streamed answers and usage."""
from __future__ import annotations
import http.client, json, os, queue, re, secrets, socket, ssl, threading, time, urllib.parse, fcntl
from contextlib import contextmanager
from . import core

NAME = 'VIGIL GLM'
ORIGIN = 'https://chat.vigilglm.ai'
CLIENT = 'ask'
CLIENT_ID = 'vigilos-ask'
PROTOCOL = 1
DEVICE_GRANT = 'urn:ietf:params:oauth:grant-type:device_code'
MODELS = ('glm-5.3-flash', 'glm-5.3')
EFFORTS = ('low', 'high', 'max')
LOOPBACK = ('127.0.0.1', 'localhost', '::1')
STALL_SECONDS = 120
RENEW_SECONDS = 60
MAX_LINE = 1024 * 1024
MAX_ANSWER_CHARS = 2_000_000
PRIVACY = ORIGIN + '/legal/privacy'
USAGE = ORIGIN + '/usage'
CONNECTED = 'Settings → Accounts → Connected desktops'
ACK = 'Understood. I will answer here, without tools.'


def origin():
    """chat.vigilglm.ai, or a test server on this computer named by VIGIL_ASK_SERVER. Tokens go nowhere else."""
    value = os.environ.get('VIGIL_ASK_SERVER')
    if not value:
        return ORIGIN
    url = urllib.parse.urlsplit(value)
    if url.scheme not in ('http', 'https') or url.hostname not in LOOPBACK or url.username or url.password or url.path not in ('', '/'):
        raise ValueError('VIGIL_ASK_SERVER must be a server on this computer.')
    return f'{url.scheme}://{url.netloc}'


def session_path():
    return core.state_dir() / 'session.json'


def valid_token(value):
    return isinstance(value, str) and 0 < len(value) <= 4096 and all(0x21 <= ord(c) <= 0x7e and c not in '";,\\' for c in value)


def _stored():
    try:
        record = json.loads(session_path().read_text())
    except (OSError, ValueError):
        return None
    return record if isinstance(record, dict) else None


def _valid(record):
    try:
        if (isinstance(record, dict) and record.get('origin') == origin() and valid_token(record.get('access_token'))
                and valid_token(record.get('refresh_token')) and isinstance(record.get('expires'), int)
                and isinstance(record.get('email'), str) and isinstance(record.get('id'), str)):
            return record
    except ValueError:
        pass
    return None


def load_session():
    """This desktop's connection to VIGIL GLM, only for the server it came from."""
    record = _stored()
    if record and 'cookie' in record:
        forget(record)  # A web session saved by VIGIL Ask 0.2; this desktop now connects with its own tokens.
        return None
    return _valid(record)


def same(a, b):
    """Whether two saved records are the same desktop connection, whichever tokens each holds now."""
    return bool(a and b and a.get('id') and a.get('id') == b.get('id') and a.get('origin') == b.get('origin'))


@contextmanager
def session_lock():
    core.private_dir(session_path().parent)
    fd = os.open(session_path().with_suffix('.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def session_record(tokens, email='', connection=None):
    """A connection record from a token reply, keeping the connection's id across rotations."""
    lifetime = tokens.get('expires_in', 900)
    if not (valid_token(tokens.get('access_token')) and valid_token(tokens.get('refresh_token'))
            and str(tokens.get('token_type', 'Bearer')).lower() == 'bearer'
            and isinstance(lifetime, int) and 0 < lifetime <= 31 * 86400):
        raise ValueError('VIGIL GLM sent tokens VIGIL Ask does not understand.')
    now = int(time.time())
    return {'origin': origin(), 'id': connection or secrets.token_hex(8), 'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'], 'expires': now + lifetime, 'email': email, 'saved': now}


def store(record):
    with session_lock():
        core.write_private(session_path(), json.dumps(record) + '\n')
    return record


def save_session(tokens, email=''):
    return store(session_record(tokens, email))


def forget(expected=None):
    """Delete the saved connection, or only `expected` if it is still the one saved."""
    with session_lock():
        current = _stored()
        if expected is None or current == expected or same(current, expected):
            session_path().unlink(missing_ok=True)


def connect(timeout):
    url = urllib.parse.urlsplit(origin())
    if url.scheme == 'https':
        return http.client.HTTPSConnection(url.hostname, url.port, timeout=timeout, context=ssl.create_default_context())
    return http.client.HTTPConnection(url.hostname, url.port, timeout=timeout)


def headers(session=None, **extra):
    sent = {'x-vigil-desktop': CLIENT, 'User-Agent': f'vigil-ask/{core.VERSION}', **extra}
    if session:
        sent['Authorization'] = f'Bearer {session["access_token"]}'
    return sent


class SignedOut(Exception):
    """VIGIL GLM has ended this desktop's connection, or another sign-in replaced it."""


def call(method, path, session=None, body=None, timeout=15):
    """One JSON request. Returns the status and the reply, {} when the reply is not a JSON object."""
    extra = {'Accept': 'application/json'}
    data = None
    if body is not None:
        data, extra['Content-Type'] = json.dumps(body).encode(), 'application/json'
    connection = connect(timeout)
    try:
        connection.request(method, path, data, headers(session, **extra))
        response = connection.getresponse()
        raw = response.read(MAX_LINE)
    finally:
        connection.close()
    try:
        reply = json.loads(raw)
    except ValueError:
        reply = {}
    return response.status, reply if isinstance(reply, dict) else {}


def _rotate(session):
    status, reply = call('POST', '/api/desktop/token/refresh', body={'client_id': CLIENT_ID, 'grant_type': 'refresh_token',
                                                                     'refresh_token': session['refresh_token']})
    if status == 200:
        return session_record(reply, session['email'], session['id'])
    if status in (400, 401) and reply.get('error') == 'invalid_grant':
        raise SignedOut()
    raise OSError(f'VIGIL GLM answered {status} when renewing the sign-in.')


def renew(session):
    """New tokens for this connection. One process renews while the others wait and use the result, because VIGIL GLM
    ends a connection whose refresh token is used twice."""
    with session_lock():
        current = _valid(_stored())
        if not same(current, session):
            raise SignedOut()
        if current['refresh_token'] != session['refresh_token']:
            return current
        try:
            current = _rotate(current)
        except SignedOut:
            session_path().unlink(missing_ok=True)
            raise
        core.write_private(session_path(), json.dumps(current) + '\n')
        return current


def fresh(session):
    return session if time.time() < session['expires'] - RENEW_SECONDS else renew(session)


def authorized(method, path, session, body=None):
    """A request under the connection, renewing the access token when it is due or VIGIL GLM turns it away once."""
    session = fresh(session)
    status, reply = call(method, path, session, body)
    if status == 401:
        session = renew(session)
        status, reply = call(method, path, session, body)
        if status == 401:
            forget(session)
            raise SignedOut()
    return status, reply


def identity(reply):
    user = reply.get('user') if isinstance(reply.get('user'), dict) else reply
    return {'email': str(user.get('email') or ''), 'name': str(user.get('name') or '')}


def account(session):
    """The connected account's email and name; raises SignedOut when the connection has ended."""
    status, reply = authorized('GET', '/api/auth/me', session)
    if status != 200:
        raise OSError(f'VIGIL GLM answered {status}.')
    return identity(reply)


def usage_line(data):
    """How much of the account's 5-hour and weekly limits is used, as one line, or '' if the answer isn't understood."""
    try:
        five, week = round(data['fiveHour']['percent']), round(data['week']['percent'])
    except (KeyError, TypeError, ValueError, OverflowError):
        return ''
    if isinstance(data.get('capped'), dict):
        return 'Usage limit reached: answers use GLM-5.3 Flash with Low thinking until it resets.'
    return f'Used {five}% of the 5-hour limit and {week}% of the weekly limit'


def usage(session):
    try:
        status, reply = authorized('GET', '/api/usage', session)
    except (OSError, ValueError, SignedOut, http.client.HTTPException):
        return ''
    return usage_line(reply) if status == 200 else ''


def revoke(session, timeout=5):
    """Ask VIGIL GLM to end this desktop's connection. True once it has, or had already."""
    try:
        if time.time() >= session['expires'] - RENEW_SECONDS:
            session = _rotate(session)
        status, _ = call('POST', '/api/desktop/session/revoke', session, {}, timeout)
    except SignedOut:
        return True
    except (OSError, ValueError, http.client.HTTPException):
        return False
    return status in (200, 204, 401)


def sign_out():
    """Disconnect this computer: the tokens go from here at once, then VIGIL GLM revokes them. False if it couldn't be reached."""
    session = load_session()
    forget()
    return revoke(session) if session else True


class Connect:
    """Connects this desktop to an account. The user signs in on VIGIL GLM in their own browser and approves the code
    shown by VIGIL Ask, so VIGIL Ask never sees a password. Events: ('code', {'user_code', 'verification_uri'}), then
    ('end', {'state', 'error', 'email'}) with state done, denied, expired, cancelled or failed."""

    def __init__(self):
        self.events = queue.Queue()
        self.stopped = threading.Event()
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def cancel(self):
        with self.lock:
            self.stopped.set()

    def _run(self):
        try:
            outcome = self._connect()
        except (OSError, http.client.HTTPException) as exc:
            outcome = {'state': 'failed', 'error': f'Could not reach VIGIL GLM: {exc}'}
        except ValueError as exc:
            outcome = {'state': 'failed', 'error': str(exc)}
        self.events.put(('end', {'error': '', 'email': '', **outcome}))

    def _connect(self):
        status, grant = call('POST', '/api/desktop/device/authorize', body={'client_id': CLIENT_ID})
        if status != 200:
            raise ValueError(f'VIGIL GLM could not start the sign-in ({grant.get("error") or status}).')
        if grant.get('protocol_version') != PROTOCOL:
            raise ValueError('This version of VIGIL Ask cannot sign in to VIGIL GLM. Update VIGIL OS, then try again.')
        code, uri = grant.get('user_code'), grant.get('verification_uri')
        expires, interval = grant.get('expires_in'), grant.get('interval', 5)
        page = urllib.parse.urlsplit(uri if isinstance(uri, str) else '')
        if not (valid_token(grant.get('device_code')) and isinstance(code, str) and re.fullmatch(r'[A-Za-z0-9-]{4,32}', code)
                and f'{page.scheme}://{page.netloc}' == origin() and not page.username
                and isinstance(expires, int) and 0 < expires <= 3600 and isinstance(interval, int) and 0 < interval <= 60):
            raise ValueError('VIGIL GLM sent a sign-in code VIGIL Ask does not understand.')
        self.events.put(('code', {'user_code': code, 'verification_uri': uri}))
        poll = {'client_id': CLIENT_ID, 'grant_type': DEVICE_GRANT, 'device_code': grant['device_code']}
        deadline, misses = time.monotonic() + expires, 0
        while not self.stopped.wait(interval):
            if time.monotonic() > deadline:
                return {'state': 'expired'}
            try:
                status, reply = call('POST', '/api/desktop/device/token', body=poll)
            except (OSError, http.client.HTTPException):
                misses += 1
                if misses == 3:
                    raise
                continue
            misses, error = 0, reply.get('error')
            if status == 200:
                break
            if error == 'authorization_pending':
                continue
            if error == 'slow_down':
                interval += 5
            elif error in ('access_denied', 'expired_token'):
                return {'state': 'denied' if error == 'access_denied' else 'expired'}
            else:
                raise ValueError(f'VIGIL GLM could not finish the sign-in ({error or status}).')
        else:
            return {'state': 'cancelled'}
        session = session_record(reply)
        status, who = call('GET', '/api/auth/me', session)
        if status != 200 or not identity(who)['email']:
            revoke(session)
            raise ValueError('VIGIL GLM did not confirm the account.')
        session['email'] = identity(who)['email']
        with self.lock:
            if not self.stopped.is_set():
                store(session)
                return {'state': 'done', 'email': session['email']}
        revoke(session)
        return {'state': 'cancelled'}


def conversation(turns, payload):
    """VIGIL Ask's instructions as the opening exchange, then the earlier turns and the new one."""
    messages = [{'role': 'user', 'content': (core.DATA / 'system-prompt.md').read_text()},
                {'role': 'assistant', 'content': ACK}]
    for question, answer in turns:
        messages += [{'role': 'user', 'content': question}, {'role': 'assistant', 'content': answer}]
    messages.append({'role': 'user', 'content': payload})
    if len(json.dumps(messages).encode()) > core.MAX_REQUEST_BYTES:
        raise core.ContextError('This conversation is now too long to send. Start a new question.')
    return messages


class Stream:
    """Turns /api/chat event-stream lines into ('thinking', None), ('text', chunk) and ('replace', text) events."""

    def __init__(self):
        self.text = self.error = ''
        self.done = self.thinking = False

    def feed(self, line):
        if not line.startswith('data:'):
            return []
        raw = line[5:].strip()
        if raw == '[DONE]':
            self.done = True
            return []
        try:
            event = json.loads(raw)
        except ValueError:
            return []
        if not isinstance(event, dict):
            return []
        error = event.get('error')
        error = error.get('message') if isinstance(error, dict) else error
        if isinstance(error, str) and error:
            self.error = error[:500]
            return []
        if isinstance(event.get('replace_content'), str):
            return self.set(event['replace_content'])
        choices = event.get('choices')
        delta = choices[0].get('delta') if isinstance(choices, list) and choices and isinstance(choices[0], dict) else None
        delta = delta if isinstance(delta, dict) else {}
        out = []
        thought = delta.get('reasoning_content') or (event.get('text') if event.get('type') == 'thinking' else None)
        if isinstance(thought, str) and thought and not self.thinking:
            self.thinking = True
            out.append(('thinking', None))
        chunk = delta.get('content')
        if not isinstance(chunk, str):
            chunk = event.get('text') if event.get('type') == 'content' else event.get('content')
        if isinstance(chunk, str) and chunk:
            out += self.set(self.text + chunk)
        return out

    def set(self, text):
        if len(text) > MAX_ANSWER_CHARS:
            self.error = 'The answer was longer than VIGIL Ask accepts.'
            return []
        if text.startswith(self.text):
            chunk, self.text = text[len(self.text):], text
            return [('text', chunk)] if chunk else []
        self.text = text
        return [('replace', text)]


class Run:
    """One answer, streamed in a thread. Events arrive on .events; the last is ('end', {'state', 'error'})."""

    def __init__(self, messages, model=None, effort=None, session=None):
        self.events = queue.Queue()
        self.cancelled = False
        self.connection = self.socket = None
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._run, args=(messages, model, effort, session), daemon=True)
        self.thread.start()

    def _run(self, messages, model, effort, session):
        try:
            outcome = self._ask(messages, model, effort, session or load_session())
        except TimeoutError:
            outcome = {'state': 'failed', 'error': 'VIGIL GLM stopped responding.'}
        except (OSError, http.client.HTTPException) as exc:
            outcome = {'state': 'failed', 'error': f'Could not reach VIGIL GLM: {exc}'}
        except Exception as exc:
            outcome = {'state': 'failed', 'error': f'VIGIL Ask could not read the answer: {exc}'}
        finally:
            with self.lock:
                connection, self.connection = self.connection, None
            if connection:
                connection.close()
        if self.cancelled:
            outcome = {'state': 'stopped', 'error': ''}
        self.events.put(('end', outcome))

    def _ask(self, messages, model, effort, session):
        if not session:
            return {'state': 'signin', 'error': ''}
        body = json.dumps({'model': model if model in MODELS else MODELS[0], 'thinkingEffort': effort if effort in EFFORTS else EFFORTS[0],
                           'messages': messages, 'webSearch': False, 'imageTool': False, 'browserTool': False}).encode()
        try:
            session = fresh(session)
            response = self._post(body, session)
            if response is not None and response.status == 401:
                response.read(MAX_LINE)
                session = renew(session)
                response = self._post(body, session)
        except SignedOut:
            return {'state': 'signin', 'error': ''}
        if response is None:
            return {'state': 'stopped', 'error': ''}
        if response.status != 200:
            return self.refused(response, session)
        if response.getheader('Content-Type', '').split(';')[0].strip().lower() != 'text/event-stream':
            return {'state': 'failed', 'error': 'VIGIL GLM did not send an event stream.'}
        if response.getheader('x-vigil-cap'):
            self.events.put(('notice', 'You have reached a usage limit, so this answer uses GLM-5.3 Flash with Low thinking.'))
        stream = Stream()
        while not (self.cancelled or stream.done or stream.error) and (line := response.readline(MAX_LINE)):
            if len(line) >= MAX_LINE:
                return {'state': 'failed', 'error': 'A VIGIL GLM event exceeded the size limit.'}
            for event in stream.feed(line.decode(errors='replace')):
                self.events.put(event)
        if self.cancelled:
            return {'state': 'stopped', 'error': ''}
        if stream.error:
            return {'state': 'failed', 'error': stream.error}
        if not stream.done:
            return {'state': 'failed', 'error': 'VIGIL GLM disconnected before completing the answer.'}
        if not stream.text.strip():
            return {'state': 'failed', 'error': 'VIGIL GLM sent an empty answer.'}
        return {'state': 'done', 'error': ''}

    def _post(self, body, session):
        """Send the question on a new connection that cancel() can close; None once stopped."""
        connection = connect(STALL_SECONDS)
        with self.lock:
            previous, self.connection = self.connection, connection
            if self.cancelled:
                return None
        if previous:
            previous.close()
        connection.connect()
        with self.lock:
            self.socket = connection.sock
            if self.cancelled:
                return None
        connection.request('POST', '/api/chat', body, headers(session, **{'Content-Type': 'application/json', 'Accept': 'text/event-stream'}))
        return connection.getresponse()

    def refused(self, response, session):
        try:
            message = json.loads(response.read(MAX_LINE)).get('error')
        except (ValueError, AttributeError, OSError, http.client.HTTPException):
            message = None
        message = message if isinstance(message, str) and message.strip() else f'VIGIL GLM answered {response.status}.'
        if response.status == 401:
            forget(session)
            return {'state': 'signin', 'error': message[:500]}
        return {'state': 'failed', 'error': message[:500]}

    def cancel(self):
        """Close the connection under the reading thread, which then ends the turn as stopped."""
        with self.lock:
            self.cancelled = True
            sock = self.socket
        if sock:
            try:
                socket.socket.shutdown(sock, socket.SHUT_RDWR)
            except OSError:
                pass

    def running(self):
        return self.thread.is_alive()

    def wait(self, timeout=None):
        self.thread.join(timeout)
