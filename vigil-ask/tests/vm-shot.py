"""Screenshot the installed window and check it opens at the expected setup state."""
import sys
sys.path.insert(0, '/usr/share/vigil-ask')
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from vigil_ask import core, window
QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app = QApplication(['vigil-ask-window'])
w = window.Window(open(core.runtime_dir() / 'window.lock', 'a'))
w.show()
for _ in range(20):
    app.processEvents()
w.grab().save(sys.argv[1])
print(w.state)
w.close()
sys.exit(w.state != sys.argv[2])
