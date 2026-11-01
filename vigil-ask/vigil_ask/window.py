"""The VIGIL Ask window, shared by the Plasma and i3 editions."""
from __future__ import annotations
import html, json, os, queue, threading
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, Slot, SLOT
from PySide6.QtGui import QDesktopServices, QGuiApplication, QIcon, QKeySequence, QShortcut
from PySide6.QtNetwork import QLocalServer
from PySide6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton,
                               QStackedWidget, QTextBrowser, QToolButton, QVBoxLayout, QWidget)
from . import cli, core, vigil_glm

SETUP_TEXT = {
    'admin-off': 'VIGIL Ask has been turned off on this computer.',
    'off': 'VIGIL Ask is turned off for your account.',
    'signin': ("Sign in with your VIGIL GLM account in your browser, where you can also create a free account. "
               "Questions use the account's credits, within its plan's limits."),
}


def empty(layout):
    while layout.count():
        widget = layout.takeAt(0).widget()
        if widget:
            widget.hide()
            widget.deleteLater()


class Answer(QTextBrowser):
    """Rendered Markdown that loads no images or other resources and opens only web links."""

    def __init__(self):
        super().__init__()
        self.setOpenLinks(False)
        self.anchorClicked.connect(lambda url: url.scheme() in ('http', 'https') and QDesktopServices.openUrl(url))

    def loadResource(self, kind, url):
        return None


class Prompt(QPlainTextEdit):
    def __init__(self, send):
        super().__init__()
        self.send = send
        self.setTabChangesFocus(True)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.send()
        else:
            super().keyPressEvent(event)


class Window(QWidget):
    def __init__(self, lock):
        super().__init__()
        self.lock = lock
        self.run = None
        self.turns, self.items = [], []
        self.entry_id = self.signin = None
        self.state, self.pending_submit = 'signin', False
        self.session_identity = None
        self.jobs, self.pending = queue.Queue(), 0
        self.dirty = False
        self.setWindowTitle('VIGIL Ask')
        self.setWindowIcon(QIcon.fromTheme('org.vigilos.Ask', QIcon.fromTheme('vigilos-logo')))
        self.build()
        self.timer = QTimer(self, interval=50, timeout=self.poll)
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        path = str(core.runtime_dir() / 'window.sock')
        QLocalServer.removeServer(path)
        self.server.listen(path)
        self.server.newConnection.connect(self.accept)
        self.watch_lock_screen()
        self.check_setup()

    def build(self):
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        title = QLabel('<b>VIGIL Ask</b>')
        badge = QLabel('Cloud: VIGIL GLM')
        badge.setStyleSheet('border: 1px solid #1763ef; border-radius: 4px; padding: 1px 6px;')
        badge.setToolTip('Your question and anything you attach are sent to VIGIL GLM, under your VIGIL GLM account, '
                         'and answered by GLM models from Z.ai.')
        header.addWidget(title)
        header.addStretch()
        header.addWidget(badge)
        layout.addLayout(header)
        self.pages = QStackedWidget()
        self.answer = Answer()
        self.pages.addWidget(self.answer)
        setup = QWidget()
        setup_layout = QVBoxLayout(setup)
        self.setup_label = QLabel(wordWrap=True, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.setup_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.setup_buttons = QHBoxLayout()
        setup_layout.addWidget(self.setup_label)
        setup_layout.addLayout(self.setup_buttons)
        setup_layout.addStretch()
        self.pages.addWidget(setup)
        layout.addWidget(self.pages, 1)
        self.chips = QHBoxLayout()
        attach = self.attach_button = QToolButton(text='Attach file…', toolTip='Attach a text file to the next question')
        attach.clicked.connect(self.attach_file)
        chips = QHBoxLayout()
        chips.addLayout(self.chips)
        chips.addStretch()
        chips.addWidget(attach)
        layout.addLayout(chips)
        entry = QHBoxLayout()
        self.prompt = Prompt(self.send)
        self.prompt.setPlaceholderText('Ask a question')
        self.prompt.setFixedHeight(self.prompt.fontMetrics().lineSpacing() * 3 + 16)
        self.ask_button = QPushButton('Ask', default=True)
        self.ask_button.clicked.connect(self.send)
        entry.addWidget(self.prompt, 1)
        entry.addWidget(self.ask_button)
        layout.addLayout(entry)
        footer = QHBoxLayout()
        self.status = QLabel(wordWrap=True, textFormat=Qt.TextFormat.PlainText)
        self.account = QLabel(openExternalLinks=True, textFormat=Qt.TextFormat.RichText)
        self.signout_button = QToolButton(text='Sign out', toolTip='Disconnect this computer from your VIGIL GLM account')
        self.signout_button.clicked.connect(self.sign_out)
        footer.addWidget(self.status, 1)
        footer.addWidget(self.account)
        footer.addWidget(self.signout_button)
        layout.addLayout(footer)
        actions = QHBoxLayout()
        self.stop_button = QPushButton('Stop', enabled=False)
        self.stop_button.clicked.connect(self.stop)
        self.copy_button = QPushButton('Copy answer', enabled=False)
        self.copy_button.clicked.connect(self.copy_answer)
        self.new_button = QPushButton('New question')
        self.new_button.clicked.connect(self.new_conversation)
        for button in (self.stop_button, self.copy_button, self.new_button):
            actions.addWidget(button)
        actions.addStretch()
        layout.addLayout(actions)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self.close)
        screen = QGuiApplication.screenAt(self.cursor().pos()) or QGuiApplication.primaryScreen()
        area = screen.availableGeometry()
        self.resize(min(900, int(area.width() * 0.8)), min(600, int(area.height() * 0.8)))
        self.move(area.center() - self.rect().center())

    def watch_lock_screen(self):
        try:
            from PySide6.QtDBus import QDBusConnection
        except ImportError:
            return
        QDBusConnection.sessionBus().connect('org.freedesktop.ScreenSaver', '/org/freedesktop/ScreenSaver',
                                             'org.freedesktop.ScreenSaver', 'ActiveChanged', self, SLOT('screen_locked(bool)'))

    @Slot(bool)
    def screen_locked(self, active):
        if active:
            self.stop()

    def accept(self):
        while self.server.hasPendingConnections():
            sock = self.server.nextPendingConnection()
            buffer = bytearray()
            def read(sock=sock, buffer=buffer):
                buffer.extend(bytes(sock.readAll()))
                if b'\n' in buffer:
                    sock.write(b'ok\n')
                    sock.flush()
                    sock.disconnectFromServer()
                    try:
                        request = json.loads(buffer.split(b'\n', 1)[0])
                    except ValueError:
                        return
                    if isinstance(request, dict):
                        self.apply(request)
            sock.readyRead.connect(read)
            sock.disconnected.connect(sock.deleteLater)

    def apply(self, request):
        if request.get('action') == 'signout':
            self.sign_out()
            return
        if request.get('action') == 'cancel':
            self.stop()
            return
        if request.get('action') == 'check':
            self.check_setup()
            return
        self.show()
        self.raise_()
        token = request.get('activation_token')
        if isinstance(token, str) and token and QGuiApplication.platformName() == 'wayland':
            os.environ['XDG_ACTIVATION_TOKEN'] = token
        self.activateWindow()
        os.environ.pop('XDG_ACTIVATION_TOKEN', None)
        busy = self.run is not None
        if not busy and (request.get('history') or request.get('last')):
            entries = sorted(core.load_history(), key=lambda e: e['updated'])
            entry = core.find_history(request['history']) if request.get('history') else (entries[-1] if entries else None)
            if entry:
                self.new_conversation()
                self.turns = [{'q': t['q'], 'sent': t['q'], 'a': t['a'], 'attached': [], 'state': 'done'} for t in entry['turns']]
                self.entry_id = entry['id']
                self.render()
        if not busy and (request.get('prompt') or request.get('context')):
            self.new_conversation()
        for item in request.get('context') or []:
            if isinstance(item, dict) and {'kind', 'label', 'text'} <= item.keys():
                self.add_item(item)
        notes = list(request.get('notes') or [])
        if request.get('prompt'):
            self.prompt.setPlainText(request['prompt'])
            if busy:
                notes.append('Still answering the last question; press Ask when it has finished.')
            elif request.get('submit'):
                self.pending_submit = True
        self.set_message(' '.join(notes))
        self.prompt.setFocus()
        self.maybe_submit()

    def check_setup(self):
        session = vigil_glm.load_session()
        if session and self.session_identity and not vigil_glm.same(session, self.session_identity):
            self.turns, self.entry_id = [], None
            self.render()
        if session:
            self.session_identity = session
        self.state = core.setup_state()
        ready = self.state == 'ready'
        self.pages.setCurrentIndex(0 if ready else 1)
        for widget in (self.prompt, self.ask_button, self.attach_button):
            widget.setEnabled(ready)
        session = vigil_glm.load_session()
        self.signout_button.setVisible(session is not None)
        self.account.setText(html.escape(session['email']) if session else '')
        empty(self.setup_buttons)
        if ready:
            if self.run is None:
                core.set_status('idle')
            self.refresh_usage()
            self.maybe_submit()
            return
        self.setup_label.setText(cli.notice() if self.state == 'notice' else SETUP_TEXT[self.state])
        buttons = {
            'off': [('Turn on', self.turn_on)],
            'notice': [('Continue', self.accept_notice), ('Turn off VIGIL Ask', self.turn_off)],
            'signin': [('Sign in', self.sign_in), ('Turn off VIGIL Ask', self.turn_off)],
        }.get(self.state, [])
        for label, action in buttons:
            button = QPushButton(label)
            button.clicked.connect(action)
            self.setup_buttons.addWidget(button)
        self.setup_buttons.addStretch()
        if self.state != 'admin-off' and self.run is None:
            core.set_status('off' if self.state == 'off' else 'idle' if session else 'signin')

    def refresh_usage(self):
        session = vigil_glm.load_session()
        if not session:
            return
        self.pending += 1
        threading.Thread(target=lambda: self.jobs.put(('usage', session, vigil_glm.usage(session))), daemon=True).start()
        self.timer.start()

    def maybe_submit(self):
        if self.pending_submit and self.state == 'ready' and self.run is None:
            self.pending_submit = False
            self.send()

    def turn_on(self):
        core.save_config(enabled=True)
        self.check_setup()

    def turn_off(self):
        core.save_config(enabled=False)
        self.check_setup()

    def accept_notice(self):
        core.save_config(notice_accepted=True)
        self.check_setup()

    def sign_in(self):
        from . import signin
        if self.signin is None or not self.signin.isVisible():
            self.signin = signin.SignIn(self)
            self.signin.accepted.connect(lambda: (self.set_message('Signed in'), self.check_setup()))
            self.signin.open()
        self.signin.raise_()

    def sign_out(self):
        if self.signin is not None and self.signin.isVisible():
            self.signin.reject()
        self.stop()
        session = vigil_glm.load_session()
        vigil_glm.forget()
        if session:
            threading.Thread(target=vigil_glm.revoke, args=(session,), daemon=True).start()
        if self.run is None:
            self.turns, self.entry_id = [], None
            self.render()
        else:
            self.turns_after_signout = True
        self.set_message('Signed out')
        self.check_setup()

    def add_item(self, item):
        self.items.append(item)
        size = len(item['text'].encode())
        chip = QToolButton(text=f'{item["label"]} · {size} bytes  ✕' if size < 1024 else f'{item["label"]} · {size / 1024:.1f} KiB  ✕')
        chip.setToolTip(item['text'][:400])
        chip.clicked.connect(lambda: (self.items.remove(item), chip.hide(), chip.deleteLater()))
        self.chips.addWidget(chip)

    def attach_file(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Attach a text file', str(Path.home()))
        if path:
            try:
                self.add_item(core.file_item(path))
            except (core.ContextError, OSError) as exc:
                self.set_message(str(exc))

    def clear_items(self):
        self.items = []
        empty(self.chips)

    def send(self):
        question = self.prompt.toPlainText().strip()
        if not question or self.run is not None:
            return
        if core.setup_state() != 'ready':
            self.check_setup()
            self.pending_submit = False
            return
        self.check_setup()
        try:
            payload = core.compose(question, self.items)
            messages = vigil_glm.conversation([(t['sent'], t['a']) for t in self.turns if t['state'] == 'done'], payload)
        except core.ContextError as exc:
            self.set_message(str(exc))
            return
        config = core.load_config()
        self.run = vigil_glm.Run(messages, config['model'], config['effort'])
        self.turns.append({'q': question, 'sent': payload, 'a': '', 'attached': [i['label'] for i in self.items], 'items': list(self.items), 'state': 'working'})
        self.prompt.clear()
        self.clear_items()
        self.set_running(True)
        core.set_status('working')
        self.set_message('Working…')
        self.render()
        self.timer.start()

    def set_running(self, running):
        self.stop_button.setEnabled(running)
        self.ask_button.setEnabled(not running)
        self.new_button.setEnabled(not running)
        self.ask_button.setText('Follow up' if self.turns and not running else 'Ask')
        self.prompt.setPlaceholderText('Ask a follow-up question' if self.turns else 'Ask a question')
        self.copy_button.setEnabled(bool(self.turns and self.turns[-1]['a']))

    def poll(self):
        while not self.jobs.empty():
            _, session, line = self.jobs.get_nowait()
            self.pending -= 1
            if not vigil_glm.same(vigil_glm.load_session(), session):
                continue
            self.account.setText(html.escape(session['email']) + (f' · <a href="{vigil_glm.USAGE}">{html.escape(line)}</a>' if line else ''))
        while self.run is not None:
            try:
                kind, value = self.run.events.get_nowait()
            except queue.Empty:
                break
            if kind == 'thinking':
                self.set_message('Thinking…')
            elif kind == 'text':
                self.turns[-1]['a'] += value
                self.dirty = True
            elif kind == 'replace':
                self.turns[-1]['a'] = value
                self.dirty = True
            elif kind == 'notice':
                self.set_message(value)
            elif kind == 'end':
                self.finish(value)
        if self.dirty:
            self.render()
        if self.run is None and not self.pending:
            self.timer.stop()

    def finish(self, outcome):
        self.run = None
        turn = self.turns[-1]
        state = turn['state'] = outcome['state']
        if state == 'done':
            self.entry_id = core.record_turn(turn['q'], turn['a'], self.entry_id)
            self.set_message('Done')
            self.refresh_usage()
            if not self.isActiveWindow():
                core.notify('Answer ready')
        elif state == 'signin':
            self.turns.pop()
            if not self.prompt.toPlainText().strip():
                self.prompt.setPlainText(turn['q'])
            for item in turn.get('items', []):
                self.add_item(item)
            self.set_message('Your VIGIL GLM sign-in has ended. Sign in again to ask.')
            self.check_setup()
        elif state == 'stopped':
            self.set_message('Stopped')
        else:
            self.set_message(f'Failed: {outcome["error"]}')
        if state != 'signin':
            core.set_status(state)
        self.set_running(False)
        if getattr(self, 'turns_after_signout', False):
            self.turns, self.entry_id = [], None
            self.turns_after_signout = False
            self.check_setup()
        self.render()

    def render(self):
        self.dirty = False
        bar = self.answer.verticalScrollBar()
        at_end = bar.value() >= bar.maximum() - 4
        parts = []
        for turn in self.turns:
            quoted = '\n'.join('> ' + line for line in turn['q'].splitlines())
            attached = f'\n\n*Attached: {", ".join(turn["attached"])}*' if turn['attached'] else ''
            answer = turn['a'] or ('*Waiting for the answer…*' if turn['state'] == 'working' else '')
            ending = {'stopped': '\n\n*Stopped.*', 'failed': '\n\n*Failed.*'}.get(turn['state'], '')
            parts.append(f'{quoted}{attached}\n\n{answer}{ending}')
        self.answer.setMarkdown('\n\n---\n\n'.join(parts))
        if at_end:
            bar.setValue(bar.maximum())

    def set_message(self, text):
        self.status.setText(text)

    def stop(self):
        if self.run is not None:
            self.run.cancel()
            self.set_message('Stopping…')

    def copy_answer(self):
        if self.turns and self.turns[-1]['a']:
            QGuiApplication.clipboard().setText(self.turns[-1]['a'])
            self.set_message('Answer copied')

    def new_conversation(self):
        if self.run is not None:
            return
        self.turns, self.entry_id = [], None
        self.clear_items()
        self.render()
        self.set_running(False)
        self.set_message('')
        if self.state == 'ready':
            core.set_status('idle')

    def closeEvent(self, event):
        if self.run is not None:
            self.run.cancel()
            self.run.wait(6)
        self.server.close()
        core.clear_status()
        super().closeEvent(event)


def main(request, lock):
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication(['vigil-ask-window'])
    app.setApplicationName('vigil-ask-window')
    app.setApplicationDisplayName('VIGIL Ask')
    app.setDesktopFileName('org.vigilos.Ask')
    window = Window(lock)
    window.show()
    window.apply(request)
    return app.exec()
