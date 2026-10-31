"""Screenshot the installed window once its setup check reaches the expected state."""
import sys, time
sys.path.insert(0, '/usr/share/vigil-ask')
from PySide6.QtWidgets import QApplication
from vigil_ask import core, window
app = QApplication(['vigil-ask-window'])
w = window.Window(open(core.runtime_dir() / 'window.lock', 'a'))
w.show()
deadline = time.monotonic() + 60
while w.state == 'checking' and time.monotonic() < deadline:
    app.processEvents()
    time.sleep(0.05)
for _ in range(20):
    app.processEvents()
w.grab().save(sys.argv[1])
print(w.state)
w.close()
sys.exit(w.state != sys.argv[2])
