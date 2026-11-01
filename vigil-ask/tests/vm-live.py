"""Checks against the real chat.vigilglm.ai that need no account: it gives the sign-in dialog a code to approve in the
browser, and it ends a connection it never issued, which VIGIL Ask then forgets."""
import re, sys, time, urllib.request
from unittest.mock import patch
sys.path.insert(0, '/usr/share/vigil-ask')
from vigil_ask import vigil_glm


def refused():
    vigil_glm.save_session({'access_token': 'vigil-ask-test-never-issued', 'refresh_token': 'vigil-ask-test-never-issued', 'expires_in': 3600})
    run = vigil_glm.Run(vigil_glm.conversation([], 'Say ready.'))
    while (event := run.events.get(timeout=60))[0] != 'end':
        print(event)
    print(event)
    return event[1]['state'] == 'signin' and vigil_glm.load_session() is None


def code(shot):
    from PySide6.QtWidgets import QApplication
    app = QApplication(['vigil-ask-window'])
    from vigil_ask import signin
    with patch.object(signin, 'QDesktopServices') as desktop:
        dialog = signin.SignIn()
        dialog.show()
        deadline = time.monotonic() + 60
        while not desktop.openUrl.called and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.05)
        # Two polls at VIGIL GLM's interval, each answered "authorization pending".
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.05)
        dialog.grab().save(shot)
        url = desktop.openUrl.call_args[0][0].toString() if desktop.openUrl.called else ''
        user_code, status = dialog.code.text(), dialog.status.text()
        dialog.reject()
    print(user_code, url, status)
    page = ''
    if url == vigil_glm.ORIGIN + '/desktop/verify':
        request = urllib.request.Request(url, headers={'User-Agent': 'vigil-ask-test'})
        page = urllib.request.urlopen(request, timeout=30).read().decode(errors='replace')
    print(re.findall(r'<title>([^<]*)</title>', page))
    return bool(re.fullmatch(r'[A-Za-z0-9-]{4,32}', user_code) and status.startswith('Waiting')
                and 'Connect VIGIL Ask' in page and vigil_glm.load_session() is None)


if __name__ == '__main__':
    sys.exit(not (refused() if sys.argv[1] == 'refused' else code(sys.argv[2])))
