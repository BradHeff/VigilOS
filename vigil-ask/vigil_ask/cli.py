"""Command-line entry points for VIGIL Ask."""
from __future__ import annotations
import argparse, datetime, fcntl, json, os, queue, shutil, signal, socket, subprocess, sys, time
from . import core, vigil_glm

GLYPH = '\uf0e5'
DIM = '#7a7a7a'
POLYBAR = {'idle': (DIM, 'Ask'), 'working': ('#edc652', 'Working'), 'done': ('#1763ef', 'Answer ready'),
           'stopped': (DIM, 'Stopped'), 'failed': ('#df3448', 'Failed'), 'signin': (DIM, 'Sign in')}


def notice():
    days = core.load_config()['history_days']
    kept = f'keeps your recent questions in ~/.local/state/vigil-ask for {days} days' if days else 'keeps no history'
    return ('VIGIL Ask sends your question, and anything you attach, to VIGIL GLM. It is answered in the cloud by GLM '
            'models from Z.ai, under your VIGIL GLM account, and uses that account\'s credits. Nothing is collected in the '
            f'background: text and files go only when you attach them and ask. VIGIL Ask {kept}. '
            f'VIGIL GLM\'s privacy policy is at {vigil_glm.PRIVACY}.')


def send_to_window(request):
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(3)
            sock.connect(str(core.runtime_dir() / 'window.sock'))
            sock.sendall(json.dumps(request).encode() + b'\n')
            return sock.recv(8) == b'ok\n'
    except OSError:
        return False


def open_window(request):
    """Hand the request to the running window, or become the window."""
    token = os.environ.get('XDG_ACTIVATION_TOKEN')
    if token:
        request = {**request, 'activation_token': token}
    if send_to_window(request):
        return 0
    lock = open(core.runtime_dir() / 'window.lock', 'a')
    deadline = time.monotonic() + 5
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if send_to_window(request):
                return 0
            if time.monotonic() > deadline:
                print('vigil-ask: another window is starting but not answering', file=sys.stderr)
                return 1
            time.sleep(0.1)
    try:
        from . import window
    except ImportError as exc:
        core.notify('VIGIL Ask needs the python3-pyside6 package.')
        print(f'vigil-ask: the window needs PySide6 ({exc})', file=sys.stderr)
        return 1
    return window.main(request, lock)


def gather(args):
    items, notes = [], []
    if getattr(args, 'selection', False):
        try:
            items.append(core.read_selection())
        except core.ContextError as exc:
            notes.append(str(exc))
    for path in getattr(args, 'file', None) or []:
        try:
            items.append(core.file_item(path))
        except (core.ContextError, OSError) as exc:
            notes.append(str(exc))
    return items, notes


def rofi(prompt, lines=(), extra=()):
    theme = core.DATA / 'vigil-ask.rasi'
    argv = ['rofi', '-dmenu', '-p', prompt, *(['-theme', str(theme)] if theme.is_file() else []), *extra]
    if not lines:
        argv += ['-l', '0']
    result = subprocess.run(argv, input='\n'.join(lines), capture_output=True, text=True)
    return result.stdout.rstrip('\n') if result.returncode == 0 else None


def cmd_window(args):
    items, notes = gather(args)
    request = {'action': 'open', 'context': items, 'notes': notes}
    question = sys.stdin.read().strip() if args.stdin else ''
    if question:
        request.update(prompt=question, submit=True)
    if args.history:
        request['history'] = args.history
    elif args.last:
        request['last'] = True
    return open_window(request)


def cmd_prompt(args):
    if not shutil.which('rofi'):
        return cmd_window(args)
    question = rofi('Ask', extra=['-theme-str', 'entry { placeholder: "Ask a question"; }'])
    if not question or not question.strip():
        return 0
    return open_window({'action': 'open', 'prompt': question, 'submit': True, 'context': [], 'notes': []})


def history_row(entry):
    """One line for a conversation in a history list: when it was last used and how it began."""
    return datetime.datetime.fromtimestamp(entry['updated']).strftime('%d %b %H:%M  ') + ' '.join(entry['turns'][0]['q'].split())[:120]


def cmd_history(args):
    entries = sorted(core.load_history(), key=lambda e: e['updated'], reverse=True)
    if not entries:
        core.notify('No recent questions.')
        return 0
    choice = rofi('History', [history_row(e) for e in entries], ['-format', 'i', '-i'])
    if choice is None or not choice.isdigit():
        return 0
    return open_window({'action': 'open', 'history': entries[int(choice)]['id'], 'context': [], 'notes': []})


def cmd_ask(args):
    question = ' '.join(args.question) if args.question and args.question != ['-'] else (None if sys.stdin.isatty() else sys.stdin.read())
    if not question or not question.strip():
        print('vigil-ask: give a question, or pipe one in', file=sys.stderr)
        return 2
    items, notes = gather(args)
    for note in notes:
        print(f'vigil-ask: {note}', file=sys.stderr)
    turns, entry_id = [], None
    if args.resume:
        entry = core.find_history(args.resume)
        if not entry:
            print(f'vigil-ask: no conversation {args.resume} in history', file=sys.stderr)
            return 2
        turns, entry_id = [(t['q'], t['a']) for t in entry['turns']], entry['id']
    state = core.setup_state()
    if state == 'notice':
        print(notice(), file=sys.stderr)
        if not sys.stdin.isatty() or input('Continue? [y/N] ').strip().lower() not in ('y', 'yes'):
            return 2
        core.save_config(notice_accepted=True)
        state = core.setup_state()
    messages = {'admin-off': 'VIGIL Ask is turned off on this computer.', 'off': 'VIGIL Ask is turned off; turn it on in its window.',
                'signin': 'Sign in to VIGIL GLM first: run vigil-ask signin, or press Sign in in the VIGIL Ask window.'}
    if state != 'ready':
        print(f'vigil-ask: {messages[state]}', file=sys.stderr)
        return 2
    try:
        conversation = vigil_glm.conversation(turns, core.compose(question, items))
    except core.ContextError as exc:
        print(f'vigil-ask: {exc}', file=sys.stderr)
        return 2
    stop = []
    signal.signal(signal.SIGUSR1, lambda *_: stop.append(1))
    unwatch = core.watch_screen_lock(lambda: stop.append(1))
    config = core.load_config()
    note = vigil_glm.unknown_settings(config['model'], config['effort'])
    if note:
        print(f'vigil-ask: {note}', file=sys.stderr)
    run = vigil_glm.Run(conversation, config['model'], config['effort'])
    core.set_status('working', stoppable=True)
    answer = ''
    try:
        while True:
            if stop and not run.cancelled:
                run.cancel()
            try:
                kind, value = run.events.get(timeout=0.2)
            except queue.Empty:
                continue
            if kind == 'text':
                answer += value
                sys.stdout.write(value)
                sys.stdout.flush()
            elif kind == 'replace':
                answer = value
                sys.stdout.write('\n\n' + value)
                sys.stdout.flush()
            elif kind == 'notice':
                print(f'vigil-ask: {value}', file=sys.stderr)
            elif kind == 'end':
                outcome = value
                break
    except KeyboardInterrupt:
        run.cancel()
        while (event := run.events.get())[0] != 'end':
            pass
        outcome = event[1]
    unwatch()
    if answer and not answer.endswith('\n'):
        print(flush=True)
    state = outcome['state']
    core.set_status(state)
    if state == 'done':
        entry_id = core.record_turn(question.strip(), answer, entry_id)
        if entry_id:
            print(f'vigil-ask: conversation {entry_id}', file=sys.stderr)
    elif state == 'signin':
        print(f'vigil-ask: {messages["signin"]}', file=sys.stderr)
    elif outcome['error']:
        print(f'vigil-ask: {outcome["error"]}', file=sys.stderr)
    core.clear_status()
    return {'done': 0, 'stopped': 130}.get(state, 1)


def polybar_line(state):
    if state == 'off':
        return ''
    colour, word = POLYBAR[state]
    return f'%{{F{colour}}}{GLYPH} {word}%{{F-}}'


def cmd_status(args):
    show = polybar_line if args.polybar else (lambda s: s)
    if not args.follow:
        print(show(core.current_status()))
        return 0
    last, parent = None, os.getppid()
    try:
        while os.getppid() == parent:
            line = show(core.current_status())
            if line != last:
                print(line, flush=True)
                last = line
            time.sleep(1)
    except (BrokenPipeError, KeyboardInterrupt):
        pass
    return 0


def cmd_krunner(args):
    from . import krunner
    return krunner.main()


def cmd_signin(args):
    if core.setup_state() in ('admin-off', 'off'):
        print('vigil-ask: VIGIL Ask is turned off.', file=sys.stderr)
        return 2
    flow = vigil_glm.Connect()
    try:
        while (event := flow.events.get())[0] != 'end':
            print(f'Open {event[1]["verification_uri"]} in a browser, sign in to VIGIL GLM, enter this code and choose '
                  f'Connect VIGIL Ask:\n\n    {event[1]["user_code"]}\n\nWaiting…', flush=True)
    except KeyboardInterrupt:
        flow.cancel()
        while (event := flow.events.get())[0] != 'end':
            pass
    outcome = event[1]
    if outcome['state'] == 'done':
        send_to_window({'action': 'check'})
        print(f'Signed in to VIGIL GLM as {outcome["email"]}.')
        return 0
    print('vigil-ask: ' + {'denied': 'the connection was declined.', 'expired': 'the code expired. Run vigil-ask signin again.',
                           'cancelled': 'sign-in cancelled.'}.get(outcome['state'], outcome['error']), file=sys.stderr)
    return 130 if outcome['state'] == 'cancelled' else 1


def cmd_signout(args):
    revoked = vigil_glm.sign_out()
    send_to_window({'action': 'signout'})
    core.stop_terminal_ask()
    if revoked:
        print('Signed out: this computer is disconnected from your VIGIL GLM account.')
    else:
        print(f'Signed out on this computer, but VIGIL GLM could not be reached to end the connection. '
              f'Remove it in {vigil_glm.CONNECTED} on VIGIL GLM.')
    return 0


def cmd_cancel(args):
    send_to_window({'action': 'cancel'})
    core.stop_terminal_ask()
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog='vigil-ask', description='Ask a quick question from the desktop.')
    parser.add_argument('--version', action='version', version=f'vigil-ask {core.VERSION}')
    sub = parser.add_subparsers(dest='command')
    window = sub.add_parser('window', help='open the window (the default)')
    window.add_argument('--selection', action='store_true', help='attach the primary selection')
    window.add_argument('--file', action='extend', nargs='+', help='attach text files')
    window.add_argument('--history', help='reopen a conversation from history')
    window.add_argument('--last', action='store_true', help='reopen the most recent conversation')
    window.add_argument('--stdin', action='store_true', help='ask the question read from standard input')
    window.set_defaults(func=cmd_window)
    sub.add_parser('prompt', help='ask through a Rofi prompt').set_defaults(func=cmd_prompt, selection=False, file=None, history=None, last=False, stdin=False)
    sub.add_parser('history', help='pick a recent conversation in Rofi').set_defaults(func=cmd_history)
    ask = sub.add_parser('ask', help='ask in this terminal')
    ask.add_argument('question', nargs='*', help='the question, or - to read it from stdin')
    ask.add_argument('--selection', action='store_true')
    ask.add_argument('--file', action='append')
    ask.add_argument('--resume', metavar='ID', help='follow up in a conversation from history')
    ask.set_defaults(func=cmd_ask)
    status = sub.add_parser('status', help='print the current state')
    status.add_argument('--follow', action='store_true', help='print again whenever it changes')
    status.add_argument('--polybar', action='store_true', help='format for a Polybar module')
    status.set_defaults(func=cmd_status)
    sub.add_parser('cancel', help='stop the question being answered').set_defaults(func=cmd_cancel)
    sub.add_parser('signin', help='connect this computer to a VIGIL GLM account').set_defaults(func=cmd_signin)
    sub.add_parser('signout', help='disconnect this computer from the VIGIL GLM account').set_defaults(func=cmd_signout)
    sub.add_parser('krunner', help='answer "ask" queries from KRunner; D-Bus starts it').set_defaults(func=cmd_krunner)
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or (argv[0] not in sub.choices and argv[0] not in ('-h', '--help', '--version')):
        argv.insert(0, 'window')
    args = parser.parse_args(argv)
    return args.func(args)
