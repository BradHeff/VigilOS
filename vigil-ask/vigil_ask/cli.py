"""Command-line entry points for VIGIL Ask."""
from __future__ import annotations
import argparse, datetime, fcntl, json, os, queue, shutil, signal, socket, subprocess, sys, time
from . import core, claude_code

GLYPH = '\uf0e5'
DIM = '#7a7a7a'
POLYBAR = {'idle': (DIM, 'Ask'), 'working': ('#edc652', 'Working'), 'done': ('#1763ef', 'Answer ready'),
           'stopped': (DIM, 'Stopped'), 'failed': ('#df3448', 'Failed'), 'signin': ('#df3448', 'Sign in'),
           'missing': (DIM, 'Set up')}


def notice():
    days = core.load_config()['history_days']
    kept = f'keeps your recent questions in ~/.local/state/vigil-ask for {days} days' if days else 'keeps no history'
    return ('VIGIL Ask sends your question, and anything you attach, to Anthropic. It is processed in the cloud '
            'under your Claude account. Nothing is collected in the background: text and files go only when you '
            f'attach them and ask. Claude Code keeps a transcript of each conversation in ~/.claude, and VIGIL Ask {kept}.')


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


def cmd_history(args):
    entries = sorted(core.load_history(), key=lambda e: e['updated'], reverse=True)
    if not entries:
        core.notify('No recent questions.')
        return 0
    rows = [datetime.datetime.fromtimestamp(e['updated']).strftime('%d %b %H:%M  ') + ' '.join(e['turns'][0]['q'].split())[:120]
            for e in entries]
    choice = rofi('History', rows, ['-format', 'i', '-i'])
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
    state, detail = core.setup_state()
    if state == 'notice':
        print(notice(), file=sys.stderr)
        if not sys.stdin.isatty() or input('Continue? [y/N] ').strip().lower() not in ('y', 'yes'):
            return 2
        core.save_config(notice_accepted=True)
        state, detail = core.setup_state()
    messages = {'admin-off': 'VIGIL Ask is turned off on this computer.', 'off': 'VIGIL Ask is turned off; turn it on in its window.',
                'missing': 'Claude Code is not installed. Open the VIGIL Ask window to install it.',
                'old': f'Claude Code {detail} is too old; VIGIL Ask needs {".".join(map(str, claude_code.MIN_VERSION))} or newer.',
                'signin': 'Sign in first with: claude auth login'}
    if state != 'ready':
        print(f'vigil-ask: {messages[state]}', file=sys.stderr)
        return 2
    payload = core.compose(question, items)
    stop = []
    signal.signal(signal.SIGUSR1, lambda *_: stop.append(1))
    run = claude_code.Run(core.claude_path(), payload, core.load_config()['model'], args.resume)
    core.set_status('working', stoppable=True)
    answer = []
    try:
        while True:
            if stop and not run.cancelled:
                run.cancel()
            try:
                kind, value = run.events.get(timeout=0.2)
            except queue.Empty:
                continue
            if kind == 'text':
                answer.append(value)
                sys.stdout.write(value)
                sys.stdout.flush()
            elif kind == 'retry':
                print(f'\nvigil-ask: {value}', file=sys.stderr)
            elif kind == 'end':
                outcome = value
                break
    except KeyboardInterrupt:
        run.cancel(send=False)
        while (event := run.events.get())[0] != 'end':
            pass
        outcome = event[1]
    if answer and not answer[-1].endswith('\n'):
        print(flush=True)
    state = outcome['state']
    core.set_status(state)
    if state == 'done':
        core.record_turn(outcome['session_id'], question.strip(), ''.join(answer))
    elif outcome['error']:
        print(f'vigil-ask: {outcome["error"]}', file=sys.stderr)
    if outcome['session_id']:
        print(f'vigil-ask: session {outcome["session_id"]}', file=sys.stderr)
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
    window.set_defaults(func=cmd_window)
    sub.add_parser('prompt', help='ask through a Rofi prompt').set_defaults(func=cmd_prompt, selection=False, file=None, history=None, last=False)
    sub.add_parser('history', help='pick a recent conversation in Rofi').set_defaults(func=cmd_history)
    ask = sub.add_parser('ask', help='ask in this terminal')
    ask.add_argument('question', nargs='*', help='the question, or - to read it from stdin')
    ask.add_argument('--selection', action='store_true')
    ask.add_argument('--file', action='append')
    ask.add_argument('--resume', metavar='SESSION', help='follow up in an earlier session')
    ask.set_defaults(func=cmd_ask)
    status = sub.add_parser('status', help='print the current state')
    status.add_argument('--follow', action='store_true', help='print again whenever it changes')
    status.add_argument('--polybar', action='store_true', help='format for a Polybar module')
    status.set_defaults(func=cmd_status)
    sub.add_parser('cancel', help='stop the question being answered').set_defaults(func=cmd_cancel)
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or (argv[0] not in sub.choices and argv[0] not in ('-h', '--help', '--version')):
        argv.insert(0, 'window')
    args = parser.parse_args(argv)
    return args.func(args)
