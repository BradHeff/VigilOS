#!/usr/bin/env python3
"""Fail a live-image build when critical login paths have generic SELinux labels."""
import os
from pathlib import Path
import sys
root = Path(sys.argv[1])
for relative, expected in [('etc/passwd', 'passwd_file_t'), ('etc/shadow', 'shadow_t'), ('usr/bin/lightdm' if (root/'usr/bin/lightdm').exists() else 'usr/bin/sddm', 'xdm_exec_t')]:
    label = os.getxattr(root / relative, 'security.selinux').decode().rstrip('\0')
    if label.split(':')[2] != expected:
        raise SystemExit(f'Incorrect SELinux label: {relative}: {label}')
    print(f'SELinux label verified: {relative}: {expected}')

for relative in ['etc/skel/.local', 'etc/skel/.local/share', 'home/liveuser/.local', 'home/liveuser/.local/share']:
    if not (os.stat(root / relative).st_mode & 0o200):
        raise SystemExit(f'User default directory is not owner-writable: {relative}')
    print(f'Owner-writable user defaults verified: {relative}')
