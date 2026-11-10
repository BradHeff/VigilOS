"""The VIGIL Ask window, shared by the Plasma and i3 editions."""
from __future__ import annotations
import html, json, os, queue, re, threading
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, Slot, SLOT
from PySide6.QtGui import QDesktopServices, QGuiApplication, QIcon, QKeySequence, QShortcut
from PySide6.QtNetwork import QLocalServer
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
                               QLabel, QListWidget, QPlainTextEdit, QPushButton, QStackedWidget, QTextBrowser, QToolButton,
                               QVBoxLayout, QWidget)
from . import cli, core, vigil_glm

SETUP_TEXT = {
    'admin-off': 'VIGIL Ask has been turned off on this computer.',
    'off': 'VIGIL Ask is turned off for your account.',
    'signin': ("Sign in with your VIGIL GLM account in your browser, where you can also create a free account. "
               "Questions use the account's credits, within its plan's limits."),
}
HINT = ' · Enter asks, Shift+Enter starts a new line, Esc closes'
HISTORY_DAYS = (0, 1, 7, 30, 90, 365)
FENCE = re.compile(r'^ {0,3}(`{3,}|~{3,})')


def with_copy_links(markdown, blocks):
    """The answer with a Copy code link after each fenced code block; the blocks' text is appended to blocks."""
    out, fence, code = [], None, []
    for line in markdown.split('\n'):
        out.append(line)
        found = FENCE.match(line)
        if fence is None:
            if found and not (found.group(1)[0] == '`' and '`' in line[found.end():]):
                fence, code = found.group(1), []
        elif found and found.group(1)[0] == fence[0] and len(found.group(1)) >= len(fence) and not line[found.end():].strip():
            blocks.append('\n'.join(code))
            out += ['', f'[Copy code](vigil-copy:{len(blocks) - 1})', '']
            fence = None
        else:
            code.append(line)
    return '\n'.join(out)


def empty(layout):
    while layout.count():
        widget = layout.takeAt(0).widget()
        if widget:
            widget.hide()
            widget.deleteLater()


class Answer(QTextBrowser):
    """Rendered Markdown that loads no images or other resources; the window decides what a link does."""

    def __init__(self):
        super().__init__()
        self.setOpenLinks(False)

    def loadResource(self, kind, url):
        return None


class Settings(QDialog):
    """Model, thinking effort and history, saved in ~/.config/vigil-ask/config.json."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('VIGIL Ask settings')
        config = core.load_config()
        model, effort = vigil_glm.choice(config['model'], config['effort'])
        self.model, self.effort, self.days = QComboBox(), QComboBox(), QComboBox()
        for box, values, current in ((self.model, vigil_glm.MODELS, model), (self.effort, vigil_glm.EFFORTS, effort)):
            for value in values:
                box.addItem(vigil_glm.LABELS[value], value)
            box.setCurrentIndex(values.index(current))
        days = config['history_days'] if isinstance(config['history_days'], int) and config['history_days'] >= 0 else 30
        for value in sorted({*HISTORY_DAYS, days}):
            self.days.addItem('Keep no history' if not value else '1 day' if value == 1 else f'{value} days', value)
        self.days.setCurrentIndex(self.days.findData(days))
        form = QFormLayout(self)
        form.addRow('Model', self.model)
        form.addRow('Thinking', self.effort)
        form.addRow('Keep history for', self.days)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.off_button = buttons.addButton('Turn off VIGIL Ask', QDialogButtonBox.ButtonRole.DestructiveRole)
        self.off_button.clicked.connect(self.turn_off)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def save(self):
        days = self.days.currentData()
        core.save_config(model=self.model.currentData(), effort=self.effort.currentData(), history_days=days)
        if not days:
            core.history_path().unlink(missing_ok=True)
        self.accept()

    def turn_off(self):
        core.save_config(enabled=False)
        self.accept()


class History(QDialog):
    """Recent conversations; the chosen one opens in the window, ready for a follow-up."""

    def __init__(self, entries, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Recent questions')
        self.entries = entries
        self.list = QListWidget()
        self.list.addItems([cli.history_row(entry) for entry in entries])
        self.list.setCurrentRow(0)
        self.list.itemActivated.connect(self.accept)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Open | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self.list)
        layout.addWidget(buttons)
        self.resize(600, 360)

    def chosen(self):
        row = self.list.currentRow()
        return self.entries[row]['id'] if 0 <= row < len(self.entries) else None


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
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.lock = lock
        self.run = None
        self.turns, self.items = [], []
        self.entry_id = self.signin = None
        self.state, self.pending_submit = 'signin', False
        self.session_identity = None
        self.jobs, self.pending = queue.Queue(), 0
        self.dirty = False
        self.code_blocks = []
        self.dialog = None
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
        self.model_label = QLabel(textFormat=Qt.TextFormat.PlainText)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.model_label)
        header.addWidget(badge)
        layout.addLayout(header)
        self.pages = QStackedWidget()
        self.answer = Answer()
        self.answer.anchorClicked.connect(self.open_link)
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
        self.prompt.setPlaceholderText('Ask a question' + HINT)
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
        self.history_button = QPushButton('History…', toolTip='Reopen a recent conversation')
        self.history_button.clicked.connect(self.open_history)
        self.settings_button = QPushButton('Settings…', toolTip='Model, thinking and history')
        self.settings_button.clicked.connect(self.open_settings)
        actions.addWidget(self.history_button)
        actions.addWidget(self.settings_button)
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
        for widget in (self.history_button, self.settings_button):
            widget.setEnabled(ready and self.run is None)
        config = core.load_config()
        model, effort = vigil_glm.choice(config['model'], config['effort'])
        note = vigil_glm.unknown_settings(config['model'], config['effort'])
        self.model_label.setText(f'{vigil_glm.LABELS[model]} · {vigil_glm.LABELS[effort]} thinking' + (' (check Settings)' if note else ''))
        self.model_label.setToolTip(note or 'Change the model and thinking in Settings')
        self.model_label.setVisible(ready)
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

    def refresh_usage(self, force=False):
        """Show the account's usage; VIGIL Ask asks VIGIL GLM at most once a minute unless an answer just used credits."""
        session = vigil_glm.load_session()
        if not session:
            return
        self.pending += 1
        jobs = self.jobs
        if force:
            work = lambda: jobs.put(('usage', session, vigil_glm.usage(session, 0)))
        else:
            work = lambda: jobs.put(('usage', session, vigil_glm.usage(session)))
        threading.Thread(target=work, daemon=True).start()
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

    def open_settings(self):
        self.dialog = Settings(self)
        self.dialog.finished.connect(lambda result: self.check_setup())
        self.dialog.open()

    def open_history(self):
        entries = sorted(core.load_history(), key=lambda e: e['updated'], reverse=True)
        if not entries:
            self.set_message('No recent questions.')
            return
        dialog = self.dialog = History(entries, self)
        dialog.accepted.connect(lambda: dialog.chosen() and self.apply({'action': 'open', 'history': dialog.chosen()}))
        dialog.open()

    def open_link(self, url):
        """Web links open in the browser; a Copy code link copies its block."""
        if url.scheme() == 'vigil-copy':
            index = url.path()
            if index.isdigit() and int(index) < len(self.code_blocks):
                QGuiApplication.clipboard().setText(self.code_blocks[int(index)])
                self.set_message('Code copied')
        elif url.scheme() in ('http', 'https'):
            QDesktopServices.openUrl(url)

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
        self.prompt.setPlaceholderText(('Ask a follow-up question' if self.turns else 'Ask a question') + HINT)
        ready = self.state == 'ready'
        self.history_button.setEnabled(ready and not running)
        self.settings_button.setEnabled(ready and not running)
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
            self.refresh_usage(force=True)
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
        parts, self.code_blocks = [], []
        for turn in self.turns:
            quoted = '\n'.join('> ' + line for line in turn['q'].splitlines())
            attached = f'\n\n*Attached: {", ".join(turn["attached"])}*' if turn['attached'] else ''
            answer = with_copy_links(turn['a'], self.code_blocks) or ('*Waiting for the answer…*' if turn['state'] == 'working' else '')
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
        self.timer.stop()
        if self.signin is not None:
            self.signin.reject()
        if self.run is not None:
            self.run.cancel()
            self.run.wait(6)
        self.server.close()
        self.lock.close()
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
