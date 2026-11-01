"""Connect VIGIL Ask to a VIGIL GLM account: the user signs in on VIGIL GLM in their own browser and approves the code
shown here, so VIGIL Ask never sees a password."""
from __future__ import annotations
import queue
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QGuiApplication
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout
from . import vigil_glm

ENDED = {'denied': 'The connection was declined. Get a new code to try again.',
         'expired': 'The code expired before it was approved. Get a new code to try again.'}


class SignIn(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Sign in to VIGIL GLM')
        self.flow = self.uri = None
        intro = QLabel('VIGIL Ask opens VIGIL GLM in your browser. Sign in there with email, Google or GitHub, or create '
                       'a free account, then enter this code and choose Connect VIGIL Ask.', wordWrap=True)
        self.code = QLabel(alignment=Qt.AlignmentFlag.AlignCenter, textFormat=Qt.TextFormat.PlainText)
        font = QFont('monospace')
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(26)
        font.setBold(True)
        self.code.setFont(font)
        self.code.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.status = QLabel(wordWrap=True, textFormat=Qt.TextFormat.PlainText)
        self.open_button = QPushButton('Open browser')
        self.open_button.clicked.connect(self.browse)
        self.copy_button = QPushButton('Copy code')
        self.copy_button.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.code.text()))
        self.again_button = QPushButton('Get a new code')
        self.again_button.clicked.connect(self.start)
        cancel = QPushButton('Cancel')
        cancel.clicked.connect(self.reject)
        buttons = QHBoxLayout()
        for button in (self.open_button, self.copy_button, self.again_button):
            buttons.addWidget(button)
        buttons.addStretch()
        buttons.addWidget(cancel)
        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(self.code)
        layout.addWidget(self.status)
        layout.addLayout(buttons)
        self.resize(520, 240)
        self.timer = QTimer(self, interval=100, timeout=self.poll)
        self.start()

    def start(self):
        if self.flow:
            self.flow.cancel()
        self.flow, self.uri = vigil_glm.Connect(), None
        self.code.setText('…')
        self.status.setText('Getting a code from VIGIL GLM…')
        self.open_button.setEnabled(False)
        self.copy_button.setEnabled(False)
        self.again_button.hide()
        self.timer.start()

    def poll(self):
        while True:
            try:
                kind, value = self.flow.events.get_nowait()
            except queue.Empty:
                return
            if kind == 'code':
                self.uri = value['verification_uri']
                self.code.setText(value['user_code'])
                self.status.setText(f'Waiting for you to connect VIGIL Ask at {self.uri}')
                self.open_button.setEnabled(True)
                self.copy_button.setEnabled(True)
                self.browse()
            elif kind == 'end':
                self.timer.stop()
                if value['state'] == 'done':
                    self.accept()
                    return
                self.code.setText('…')
                self.status.setText(ENDED.get(value['state'], value['error']))
                self.open_button.setEnabled(False)
                self.copy_button.setEnabled(False)
                self.again_button.show()
                return

    def browse(self):
        if self.uri:
            QDesktopServices.openUrl(QUrl(self.uri))

    def done(self, result):
        """However the dialog closes, an unfinished sign-in stops and saves nothing."""
        if self.flow:
            self.flow.cancel()
        self.timer.stop()
        super().done(result)
