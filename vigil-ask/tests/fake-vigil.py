#!/usr/bin/python3
"""Stands in for chat.vigilglm.ai in tests: desktop sign-in, account, usage and the /api/chat event stream.
Modes: ok, slow, stalled, truncated, auth, credits, cap, error, crash, replace. Run alone as: fake-vigil.py PORT LOG [MODE].
The tokens in TOKENS are already connected, for tests that start signed in."""
import http.server, json, secrets, sys, threading, time, urllib.parse

CLIENT_ID = 'vigilos-ask'
TOKENS = {'access_token': 'fake-access-1', 'refresh_token': 'fake-refresh-1', 'token_type': 'Bearer', 'expires_in': 3600}
EMAIL = 'tester@example.invalid'
ANSWER = ['Fake ', 'answer ', 'for ', 'tests.']
USAGE = {'plan': 'free', 'percent': 12, 'byEffort': {}, 'fiveHour': {'percent': 12, 'credits': 5600, 'budget': 46667, 'resetsAt': None},
         'week': {'percent': 3, 'credits': 7000, 'budget': 233333, 'resetsAt': None}}


class Fake(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port=0, log=None, mode='ok'):
        super().__init__(('127.0.0.1', port), Handler)
        self.log, self.mode, self.requests = log, mode, []
        self.disconnected = threading.Event()
        self.lock = threading.Lock()
        self.access = {TOKENS['access_token']: 'desktop-1'}
        self.refresh = {TOKENS['refresh_token']: 'desktop-1'}
        self.used, self.revoked, self.devices, self.codes = {}, set(), {}, 0

    @property
    def url(self):
        return f'http://127.0.0.1:{self.server_address[1]}'

    def record(self, entry):
        self.requests.append(entry)
        if self.log:
            with open(self.log, 'a') as stream:
                stream.write(json.dumps(entry) + '\n')

    def start(self):
        threading.Thread(target=self.serve_forever, daemon=True).start()
        return self

    def decide(self, decision='approve'):
        """What the account holder chose on the verify page: approve, deny or expire."""
        with self.lock:
            for device in self.devices.values():
                device['decision'] = device['decision'] or decision

    def expire_access(self):
        with self.lock:
            self.access.clear()

    def issue(self, desktop):
        access, refresh = 'fake-access-' + secrets.token_hex(6), 'fake-refresh-' + secrets.token_hex(6)
        self.access[access] = self.refresh[refresh] = desktop
        return {'access_token': access, 'refresh_token': refresh, 'token_type': 'Bearer', 'expires_in': 3600, 'scope': 'ask'}

    def desktop(self, authorization):
        token = authorization[7:] if authorization.startswith('Bearer ') else ''
        with self.lock:
            desktop = self.access.get(token)
            return desktop if desktop and desktop not in self.revoked else None


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *args):
        pass

    def signed_in(self):
        return self.server.desktop(self.headers.get('Authorization') or '')

    def reply(self, status, body=b'', kind='application/json', extra=()):
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(body)))
        for name, value in extra:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def json(self, status, body):
        self.reply(status, json.dumps(body).encode())

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path == '/desktop/verify':
            self.reply(200, b'<!doctype html><title>Connect VIGIL Ask</title>Enter the code shown in VIGIL Ask', 'text/html')
        elif path in ('/api/auth/me', '/api/usage'):
            if not self.signed_in():
                self.json(401, {'error': 'Not authenticated'})
            else:
                self.json(200, {'email': EMAIL, 'name': 'Tester', 'role': 'USER'} if path == '/api/auth/me' else USAGE)
        else:
            self.json(404, {'error': 'Not found'})

    def do_POST(self):
        path = urllib.parse.urlsplit(self.path).path
        raw = self.rfile.read(int(self.headers.get('Content-Length') or 0))
        try:
            body = json.loads(raw)
        except ValueError:
            body = None
        if path.startswith('/api/desktop/'):
            self.server.record({'path': path})
            if not isinstance(body, dict):
                self.json(400, {'error': 'invalid_request'})
            else:
                self.desktop_route(path, body)
            return
        if path != '/api/chat':
            self.json(404, {'error': 'Not found'})
            return
        seen = {k.lower(): v for k, v in self.headers.items() if k.lower() in ('authorization', 'cookie', 'x-vigil-desktop', 'accept', 'user-agent')}
        self.server.record({'path': path, 'headers': seen, 'body': body})
        mode = self.server.mode
        if not self.signed_in():
            self.json(401, {'error': 'Create a free account or sign in to use chat.', 'code': 'registration_required'})
        elif mode == 'auth':
            with self.server.lock:
                self.server.revoked.update(self.server.access.values())
            self.json(401, {'error': 'Your session has ended.'})
        elif mode == 'credits':
            self.json(402, {'error': 'Insufficient credits'})
        elif mode == 'crash':
            self.reply(500, b'<html>Internal error</html>', 'text/html')
        else:
            self.stream(mode)

    def desktop_route(self, path, body):
        server = self.server
        with server.lock:
            if path == '/api/desktop/session/revoke':
                desktop = server.access.get((self.headers.get('Authorization') or '')[7:])
                if not desktop or desktop in server.revoked:
                    self.json(401, {'error': 'Not authenticated'})
                    return
                server.revoked.add(desktop)
                self.json(200, {'ok': True})
                return
            if body.get('client_id') != CLIENT_ID:
                self.json(400, {'error': 'invalid_client'})
            elif path == '/api/desktop/device/authorize':
                code = secrets.token_urlsafe(32)
                server.codes += 1
                user_code = f'TEST-{server.codes:04d}'
                server.devices[code] = {'user_code': user_code, 'decision': None}
                self.json(200, {'protocol_version': 1, 'device_code': code, 'user_code': user_code,
                                'verification_uri': server.url + '/desktop/verify', 'expires_in': 600, 'interval': 1})
            elif path == '/api/desktop/device/token':
                device = server.devices.get(body.get('device_code'))
                if body.get('grant_type') != 'urn:ietf:params:oauth:grant-type:device_code':
                    self.json(400, {'error': 'invalid_request'})
                elif not device:
                    self.json(400, {'error': 'invalid_grant'})
                elif device['decision'] is None:
                    self.json(400, {'error': 'authorization_pending'})
                else:
                    del server.devices[body['device_code']]
                    if device['decision'] == 'approve':
                        self.json(200, server.issue('desktop-' + secrets.token_hex(4)))
                    else:
                        self.json(400, {'error': 'access_denied' if device['decision'] == 'deny' else 'expired_token'})
            elif path == '/api/desktop/token/refresh':
                token = body.get('refresh_token')
                if body.get('grant_type') != 'refresh_token':
                    self.json(400, {'error': 'invalid_request'})
                elif token in server.used:
                    server.revoked.add(server.used[token])
                    self.json(400, {'error': 'invalid_grant'})
                elif (desktop := server.refresh.pop(token, None)) is None or desktop in server.revoked:
                    self.json(400, {'error': 'invalid_grant'})
                else:
                    server.used[token] = desktop
                    self.json(200, server.issue(desktop))
            else:
                self.json(404, {'error': 'Not found'})

    def stream(self, mode):
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Connection', 'close')
        if mode == 'cap':
            self.send_header('x-vigil-cap', json.dumps({'window': 'fiveHour', 'resetsAt': '2026-11-01T05:00:00Z'}))
        self.end_headers()
        frames = [{'choices': [{'delta': {'reasoning_content': 'Considering the question.'}}]}]
        frames += [{'choices': [{'delta': {'content': chunk}}]} for chunk in ANSWER]
        if mode == 'error':
            frames = frames[:2] + [{'error': 'The model failed'}]
        if mode == 'truncated':
            frames = frames[:2]
        if mode == 'replace':
            frames.append({'replace_content': 'Fixed answer.'})
        frames.append({'usage': {'prompt_tokens': 10, 'completion_tokens': 4}})
        try:
            self.wfile.write(b': keep-alive\n\n')
            for frame in frames:
                self.wfile.write(f'data: {json.dumps(frame)}\n\n'.encode())
                self.wfile.flush()
                if mode == 'stalled' and frame == frames[1]:
                    time.sleep(5)
                for _ in range(100 if mode == 'slow' else 0):
                    time.sleep(0.05)
                    self.wfile.write(b': keep-alive\n\n')
                    self.wfile.flush()
            if mode != 'truncated':
                self.wfile.write(b'data: [DONE]\n\n')
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            self.server.record({'path': '/api/chat', 'disconnected': True})
            self.server.disconnected.set()
        self.close_connection = True


if __name__ == '__main__':
    fake = Fake(int(sys.argv[1]), sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else 'ok')
    print(fake.url, flush=True)
    fake.serve_forever()
