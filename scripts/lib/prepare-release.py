#!/usr/bin/env python3
"""Render allocated product identity in an owned disposable prepared root."""
from pathlib import Path
import configparser
import json
import os
import re
import subprocess
import sys
sys.dont_write_bytecode = True
from version import source_release


def prepare_release(root, release, desktop):
    """Render the allocated identity into the prepared product root."""
    if desktop not in ('kde', 'i3'):
        raise ValueError('Unknown desktop')
    root = Path(root)
    version, code = release.version, release.codename
    variant = 'KDE Plasma' if desktop == 'kde' else 'i3'
    files = {
        'usr/lib/os-release': f'''NAME="VIGIL OS"
VERSION="{version} ({code})"
ID=vigilos
ID_LIKE=fedora
VERSION_ID={version}
VERSION_CODENAME={release.codename_id}
BUILD_ID={release.build_id}
PRETTY_NAME="VIGIL OS {version} ({code})"
ANSI_COLOR="0;38;2;129;212;250"
LOGO=vigilos-logo
CPE_NAME="cpe:/o:vigilos:vigilos:{version}"
VARIANT="{variant}"
VARIANT_ID={desktop}
HOME_URL="https://vigilglm.ai"
DOCUMENTATION_URL="https://docs.vigilglm.ai"
SUPPORT_URL="https://support.vigilglm.ai"
BUG_REPORT_URL="https://github.com/vigilglm/vigilos/issues"
PRIVACY_POLICY_URL="https://vigilglm.ai/privacy"
DEVELOPER="Brad Heffernan"
''',
        'etc/vigilos-release': f'VIGIL OS release {version} ({code})\n',
        'etc/issue': f'VIGIL OS {version} ({code}) \\r (\\l)\n\n',
        'etc/issue.net': f'VIGIL OS {version} ({code})\n',
        'etc/lsb-release': f'''DISTRIB_ID="VIGIL OS"
DISTRIB_RELEASE={version}
DISTRIB_CODENAME={release.codename_id}
DISTRIB_DESCRIPTION="VIGIL OS {version} ({code})"
DISTRIB_DEVELOPER="Brad Heffernan"
''',
        'usr/lib/vigilos/release.json': json.dumps(release.record(), indent=2) + '\n',
    }
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if name in ('etc/issue', 'etc/issue.net'): path.unlink(missing_ok=True)
        path.write_text(text)
    link = root / 'etc/os-release'
    link.unlink(missing_ok=True)
    link.symlink_to('../usr/lib/os-release')
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read(root / '.buildstamp')
    if not cfg.has_section('Main'): cfg.add_section('Main')
    cfg['Main'].update(Product='VIGIL OS', Version=version, IsFinal='False')
    with (root / '.buildstamp').open('w') as stream: cfg.write(stream)

    for base in [root, root.parent / 'new_iso']:
        for folder in ['boot/grub2/themes/vigilos', 'usr/share/grub/themes/vigilos', 'EFI/BOOT/themes/vigilos']:
            path = base / folder / 'theme.txt'
            if path.is_file():
                text = re.sub(r'text = "VIGIL OS [0-9]+\.[0-9]+"', f'text = "VIGIL OS {version}"', path.read_text())
                path.write_text(text)
    path = root / 'usr/share/sddm/themes/vigilos/metadata.desktop'
    if path.is_file():
        path.write_text(re.sub(r'^Version=.*$', f'Version={version}', path.read_text(), flags=re.MULTILINE))


def main():
    if os.environ.get('VIGIL_BUILD_GUEST') != '1' or not Path('/etc/vigilos-disposable-builder').is_file():
        raise SystemExit('ERROR: Run only in the approved disposable builder VM.')
    subprocess.run(['systemd-detect-virt', '--vm', '--quiet'], check=True)
    root = Path(sys.argv[1]).resolve()
    if root.name != 'squashfs' or not (root.parent / '.vigilos-owned').is_file():
        raise SystemExit('Owned prepared VIGIL root required')
    release = source_release()
    prepare_release(root, release, os.environ.get('VIGIL_DESKTOP', 'kde'))
    print(f'Product identity prepared: VIGIL OS {release.version} ({release.codename}), build ID {release.build_id}')


if __name__ == '__main__':
    main()
