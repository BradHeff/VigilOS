#!/usr/bin/env python3
"""Static, unprivileged validation; never executes build code."""
import ast, hashlib, os, re, shutil, subprocess, tempfile, tomllib
from pathlib import Path
root=Path(__file__).resolve().parents[2]
required=['scripts/build-and-brand.sh','scripts/lib/build.py','scripts/lib/build-guest.sh','scripts/lib/remix.sh','scripts/lib/install-i3.sh','scripts/lib/guest-setup.sh','branding/logos/source/vigil-mark.svg','branding/i3/skel/.git-prompt.bash','branding/i3/fonts/Feather-LICENSE','branding/i3/rofi-LICENSE']
for name in required:assert (root/name).is_file(),f'Missing {name}'
for directory in [root/'scripts',root/'branding/i3/bin']:
    for path in directory.rglob('*'):
        if not path.is_file():continue
        if path.suffix=='.py' or path.read_bytes().startswith((b'#!/usr/bin/python3',b'#!/usr/bin/env python3')):ast.parse(path.read_text(),filename=str(path))
        elif path.read_bytes().startswith((b'#!/bin/bash',b'#!/usr/bin/env bash',b'#!/usr/bin/bash',b'#!/bin/sh',b'#!/usr/bin/env sh')):
            subprocess.run(['bash','-n',path],check=True)
print('PASS: shell syntax and Python AST')
assets=root/'branding/i3'
for relative,digest in {'vendor/greenclip-v4.2':'80b189fc9ce2e0a56e33be642875f5c3fb53647465f8024a541621307a6a290f','vendor/i3lock-color-2.13.c.5.tar.gz':'46f15cbbf339873266e014f70b5e1ec02177f0295302b615a7bd85bef40d8ad2'}.items():assert hashlib.sha256((assets/relative).read_bytes()).hexdigest()==digest,relative
wallpaper=root/'branding/wallpapers/VIGILOS/contents/images/1672x941.png'
assert hashlib.sha256(wallpaper.read_bytes()).hexdigest()=='58f1ea66fc85ad7fa71358fb6e20ee78587600985bae92319b08d7bd078218ca'
assert wallpaper.stat().st_mode & 0o444 == 0o444
print('PASS: pinned vendor inputs and shared VIGIL wallpaper')
config=assets/'skel/.config/i3/config';text=config.read_text()
assert not re.search(r'^\s*#',text,re.M),'Commented lines remain in shipped i3 config'
for directory in [assets/'skel',assets/'bin']:
    for path in directory.rglob('*'):
        if path.is_file():
            value=path.read_text()
            assert not re.search(r'/home/bheffernan|\.screenlayout|NVD_BACKEND|LIBVA_DRIVER_NAME|Mirasol|Horizon AD',value),path
bar=(assets/'skel/.config/polybar/config.ini').read_text()
assert 'nmem' not in bar and 'nvidia' not in bar.lower()
assert 'brave-browser' in text and 'vigil-wallpaper' in text
assert (assets/'skel/.bashrc.d/50-vigilos-i3.sh').is_file() and not (assets/'skel/.bashrc').exists(), 'Preserve native bash skeleton ownership'
cfg=tomllib.loads((assets/'skel/.config/alacritty/alacritty.toml').read_text())
assert cfg['general']['import']==['~/.config/alacritty/colors.toml']
tomllib.loads((assets/'skel/.config/alacritty/colors.toml').read_text())
for shell_file in ['skel/.bashrc.d/50-vigilos-i3.sh','skel/.git-prompt.bash']:
    subprocess.run(['bash','-n',assets/shell_file],check=True)
if shutil.which('i3'):
    with tempfile.TemporaryDirectory(prefix='vigil-i3-check-') as runtime:
        subprocess.run(['i3','-C','-c',config],check=True,env={**os.environ,'XDG_RUNTIME_DIR':runtime})
print('PASS: clean portable i3 defaults, terminal imports and prompt')
for path in (root/'scripts').rglob('*'):
    if path.is_file() and path.suffix in ['.sh','.py']:
        for ref in re.findall(r'scripts/([\w./-]+\.(?:sh|py))',path.read_text()):
            assert (root/'scripts'/ref).is_file(),f'Broken helper reference {path}: {ref}'
print('PASS: active script references; all checks passed')

for name in ['build-i3-lock.sh','build-guest.sh','remix.sh','install-i3.sh','install-default-apps.sh','package-branding.sh','package-release-common.sh','package-wallpaper-compat.sh','pack-prepared-root.sh','finish-prepared-image.sh','prepare-brand-assets.sh']:
    result=subprocess.run(['bash',root/'scripts/lib'/name],env={**os.environ,'VIGIL_BUILD_GUEST':'0'},capture_output=True,text=True,timeout=10)
    assert result.returncode!=0 and 'approved disposable builder' in result.stderr, f'Broken host guard/helper path: {name}: {result.stderr}'
print('PASS: every internal build entry refuses host execution through its real guard')

for path in (assets/'appearance').rglob('*'):
    if path.is_symlink():
        assert not os.readlink(path).startswith('/home/'),f'Personal theme symlink: {path}'
print('PASS: imported appearance assets have no personal-home symlink targets')
