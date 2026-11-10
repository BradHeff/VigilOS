#!/usr/bin/env python3
"""Static, unprivileged validation; never executes build code."""
import ast, configparser, hashlib, json, os, re, runpy, shutil, struct, subprocess, tempfile, tomllib
from pathlib import Path
import sys
sys.dont_write_bytecode=True
from version import load_config, source_release
root=Path(__file__).resolve().parents[2]
required=['scripts/build-and-brand.sh','scripts/lib/build.py','version.json','scripts/lib/version.py','scripts/lib/product-version.sh','scripts/lib/prepare-release.py','scripts/lib/test-versioning.py','scripts/lib/build-guest.sh','scripts/lib/remix.sh','scripts/lib/install-i3.sh','scripts/lib/guest-setup.sh','branding/logos/source/vigil-mark.svg','branding/i3/skel/.git-prompt.bash','branding/i3/fonts/Feather-LICENSE','branding/i3/rofi-LICENSE']
for name in required:assert (root/name).is_file(),f'Missing {name}'
for directory in [root/'scripts',root/'branding/i3/bin',root/'vigil-ask']:
    for path in directory.rglob('*'):
        if not path.is_file():continue
        if path.suffix=='.py' or path.read_bytes().startswith((b'#!/usr/bin/python3',b'#!/usr/bin/env python3')):ast.parse(path.read_text(),filename=str(path))
        elif path.read_bytes().startswith((b'#!/bin/bash',b'#!/usr/bin/env bash',b'#!/usr/bin/bash',b'#!/bin/sh',b'#!/usr/bin/env sh')):
            subprocess.run(['bash','-n',path],check=True)
version_config=load_config(root/'version.json')
release=source_release(root)
if (root/'release.json').exists():
    assert version_config['build_number']==release.build_number and version_config['codename']==release.codename
    assert version_config['next_version_number']==release.version_number+1
print(f'PASS: shell syntax, Python AST and version metadata ({release.version}, {release.codename})')
if shutil.which('shellcheck'):
    shell=re.compile(rb'#!\S*(/env )?\S*\b(ba)?sh\b')
    scripts=sorted(p.relative_to(root) for p in [*(root/'scripts').rglob('*'),*(root/'branding/i3').rglob('*'),*(root/'vigil-ask').rglob('*')]
                   if p.is_file() and not p.is_symlink() and 'appearance' not in p.parts and (p.suffix=='.sh' or shell.match(p.read_bytes()[:80])))
    subprocess.run(['shellcheck','-x','-S','error',*map(str,scripts)],check=True,cwd=root)
    print(f'PASS: ShellCheck finds no errors in {len(scripts)} shell scripts')
else:
    print('SKIP: ShellCheck is not installed here; the builder and CI run it')
assets=root/'branding/i3'
for relative,digest in {'vendor/greenclip-v4.2':'80b189fc9ce2e0a56e33be642875f5c3fb53647465f8024a541621307a6a290f','vendor/i3lock-color-2.13.c.5.tar.gz':'46f15cbbf339873266e014f70b5e1ec02177f0295302b615a7bd85bef40d8ad2'}.items():assert hashlib.sha256((assets/relative).read_bytes()).hexdigest()==digest,relative
wallpaper=root/'branding/wallpapers/VIGILOS/contents/images/3840x2160.png'
assert hashlib.sha256(wallpaper.read_bytes()).hexdigest()=='de5f2e826828bde96f19ea936ffc3caada822692e4ff5c86c0930645b29be2b0'
assert wallpaper.stat().st_mode & 0o444 == 0o444
manifest=json.loads((root/'branding/wallpapers/dark-assets.json').read_text())
for name,info in manifest['variants'].items():
    for path in [root/'branding/wallpapers'/name,wallpaper.parent/name.removeprefix('VIGIL-')]:
        data=path.read_bytes()
        assert hashlib.sha256(data).hexdigest()==info['sha256'],path
        assert struct.unpack('>II',data[16:24])==(info['width'],info['height']),path
assert not (wallpaper.parent/'1672x941.png').exists(),'Old city must not remain an active wallpaper choice'
def jpeg_size(data):
    i=2
    while data[i]==0xFF:
        marker,length=data[i+1],struct.unpack('>H',data[i+2:i+4])[0]
        if 0xC0<=marker<=0xCF and marker not in (0xC4,0xC8,0xCC):
            height,width=struct.unpack('>HH',data[i+5:i+9]);return width,height
        i+=2+length
    raise ValueError('no JPEG frame header')
desktop=json.loads((root/'branding/wallpapers/desktop-assets.json').read_text())
assert hashlib.sha256((root/'branding/wallpapers/wallpaper.png').read_bytes()).hexdigest()==desktop['source']['sha256']
images=root/'branding/wallpapers/VIGILOS-Desktop/contents/images'
assert sorted(p.name for p in images.iterdir())==sorted(desktop['variants'])
for name,info in desktop['variants'].items():
    data=(images/name).read_bytes()
    assert hashlib.sha256(data).hexdigest()==info['sha256'],name
    assert jpeg_size(data)==(info['width'],info['height'])and name==f"{info['width']}x{info['height']}.jpg",name
assert 'wallpapers/VIGILOS-Desktop' in (root/'scripts/lib/package-wallpaper-compat.sh').read_text()
credit='https://www.deviantart.com/byrotek'
assert credit in (root/'LICENSES/NOTICE.txt').read_text() and credit in (root/'README.md').read_text(),'Keep the wallpaper artist credit'
assert json.loads((images.parent.parent/'metadata.json').read_text())['KPlugin']['Authors'][0]['Website']==credit
login_art='/usr/share/vigilos/wallpapers/VIGILOS/contents/images/3840x2160.png'
for path in ['Skel/.config/kscreenlockerrc','branding/i3/bin/lock','scripts/lib/install-i3.sh']:
    assert login_art in (root/path).read_text(),f'{path} must keep the dark artwork'
for folder in ['branding/sddm/vigilos']:
    assert hashlib.sha256((root/folder/'background.png').read_bytes()).hexdigest()==manifest['preserved_sddm']['sha256']
    cfg=configparser.ConfigParser();cfg.read(root/folder/'theme.conf');colors=cfg['General']
    def lightness(color):
        rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)]
        linear=[v/12.92 if v<=0.04045 else ((v+0.055)/1.055)**2.4 for v in rgb]
        return sum(v*w for v,w in zip(linear,[.2126,.7152,.0722]))
    for foreground,background in [(colors['input_text_color'],colors['input_background']),(colors['placeholder_color'],colors['input_background']),(colors['color'],'#1e1e1e'),('#ffffff','#315cb9')]:
        a,b=sorted([lightness(foreground),lightness(background)])
        assert (b+.05)/(a+.05)>=4.5,(folder,foreground,background)
    assert 'Image.PreserveAspectFit' in (root/folder/'Main.qml').read_text()
    main=(root/folder/'Main.qml').read_text()
    assert 'VigilComponents.VirtualKeyboardLoader {' in main, 'Use the bundled keyboard loader, not private Breeze exports'
    for qml in ['Main.qml','Login.qml']:
        assert not re.search(r'\bunits\.', (root/folder/qml).read_text()), 'Use explicit Kirigami.Units on current Plasma'
    for component in ['VirtualKeyboardLoader.qml','VirtualKeyboard.qml','VirtualKeyboard_wayland.qml']:
        assert (root/folder/'components'/component).is_file(), (folder,component)
defaults=(root/'branding/desktop-defaults/defaults').read_text()
for value in ['ColorScheme=VIGILDark','name=PurPurNight-Plasma','Theme=VIGIL-Dark-Splash']:
    assert value in defaults,value
assert 'desktop-image-scale-method: "padding"' in (root/'branding/grub/vigilos/theme.txt').read_text()
assert '--max --color=1e1e1e' in (root/'branding/i3/bin/lock').read_text()
for profile in ['Skel','branding/i3/skel']:
    for version in ['3','4']:
        cfg=configparser.ConfigParser();cfg.read(root/profile/f'.config/gtk-{version}.0/settings.ini')
        assert cfg.getboolean('Settings','gtk-application-prefer-dark-theme')
cursor='Qogir-white-cursors'
for path,value in [('branding/desktop-defaults/defaults',f'cursorTheme={cursor}'),('Skel/.config/kcminputrc',f'cursorTheme={cursor}'),
                   ('Skel/.config/gtk-3.0/settings.ini',f'gtk-cursor-theme-name={cursor}'),('Skel/.config/gtk-4.0/settings.ini',f'gtk-cursor-theme-name={cursor}'),
                   ('branding/i3/skel/.Xresources',f'Xcursor.theme: {cursor}'),('scripts/lib/install-i3.sh',f'cursor-theme-name={cursor}'),
                   ('scripts/lib/remix.sh',f'CursorTheme={cursor}'),('scripts/lib/remix.sh',f'cursorTheme={cursor}')]:
    assert value in (root/path).read_text(),(path,value)
assert (root/'branding/cursors'/cursor/'index.theme').is_file()
konsole=configparser.ConfigParser(interpolation=None);konsole.optionxform=str
konsole.read(root/'branding/colourscheme/VIGILDark-Konsole.colorscheme')
assert max(map(int,konsole['Background']['Color'].split(',')))<=48,'Konsole background must stay dark'
assert 'ColorScheme=VIGILDark-Konsole' in (root/'scripts/lib/remix.sh').read_text()
print('PASS: pinned vendor inputs, preserved dark login artwork, sized desktop wallpaper, dark defaults, cursor and login contrast')
gtk2=(assets/'skel/.gtkrc-2.0').read_text()
assert 'gtk-theme-name="VALYRIAN-Total-Steel"' in gtk2
assert 'Requires: gtk-murrine-engine' in (root/'scripts/lib/install-i3.sh').read_text()
wallpaper_setup=(root/'scripts/runtime/vigilos-wallpaper-default.js').read_text()
assert 'containment.writeConfig("FillMode", 1)' in wallpaper_setup
assert 'containment.writeConfig("Color", "#1e1e1e")' in wallpaper_setup
assert "d/'org.kde.plasma.folder.js'" in (root/'scripts/lib/prepare-desktop-defaults.py').read_text()
overrides=runpy.run_path(str(root/'scripts/lib/prepare-repository-overrides.py'))['repository_overrides']
sample='[fedora]\nname=Fedora $releasever\nmetalink=https://mirrors.fedoraproject.org/metalink?repo=fedora-$releasever&arch=$basearch\ngpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-${releasever}-$basearch\ngpgcheck=1\nsslverify=1\nenabled=1\n[updates]\nmetalink=https://mirrors.fedoraproject.org/metalink?repo=updates-released-f$releasever&arch=$basearch\n'
repo_cfg=configparser.ConfigParser(interpolation=None);repo_cfg.read_string(overrides({'fedora.repo':sample}))
assert 'fedora-44&arch=$basearch' in repo_cfg['fedora']['metalink']
assert repo_cfg['fedora']['gpgkey'].endswith('fedora-44-$basearch')
assert 'updates-released-f44&arch=$basearch' in repo_cfg['updates']['metalink']
assert not any(k in repo_cfg['fedora'] for k in ['enabled','gpgcheck','sslverify','skip_if_unavailable'])
assert 'system-release(releasever) = 44' in (root/'scripts/lib/package-branding.sh').read_text()
print('PASS: Fedora base URL/key overrides preserve native security settings, GTK2 engine/default and uncropped desktop defaults')
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
ask=root/'vigil-ask'
spec=(ask/'vigil-ask.spec').read_text()
shipped=[p for p in [ask/'vigil-ask',ask/'vigil-ask.spec',*(ask/'vigil_ask').glob('*.py'),*(ask/'data').iterdir(),*(ask/'system').iterdir()] if p.is_file()]
assert not [p for p in shipped if re.search(r'claude|anthropic',p.read_text(),re.I)],'VIGIL Ask must not ship Claude Code parts'
assert not list((root/'branding/repos').rglob('*claude*')),'No Claude Code repository or key ships'
glm=(ask/'vigil_ask/vigil_glm.py').read_text()
assert "ORIGIN = 'https://chat.vigilglm.ai'" in glm and "LOOPBACK = ('127.0.0.1', 'localhost', '::1')" in glm,'Tokens go only to chat.vigilglm.ai or a local test server'
assert "'webSearch': False, 'imageTool': False, 'browserTool': False" in glm,'Quick Ask asks without tools'
assert 'api_key' not in glm.lower() and 'vig_' not in glm,'VIGIL Ask signs in to the account; it never takes an API key'
sign=(ask/'vigil_ask/signin.py').read_text()
assert "CLIENT_ID = 'vigilos-ask'" in glm and "'Authorization'" in glm and 'WebEngine' not in sign and 'vigil_glm.Connect()' in sign,'VIGIL Ask signs in with a code approved in the browser and never sees a password'
if shutil.which('desktop-file-validate'):
    for entry in ['org.vigilos.Ask.desktop','vigil-ask-sendto.desktop','vigil-ask-krunner.desktop']:subprocess.run(['desktop-file-validate',ask/'system'/entry],check=True)
i3_text=(assets/'skel/.config/i3/config').read_text()
assert not re.search(r'^\s*set\s+\$\S+\s+.*\$',i3_text,re.M),'i3 does not expand a variable inside another variable'
for value in ['bindsym $mod+Shift+a exec --no-startup-id vigil-ask prompt','bindsym $mod+Ctrl+a exec --no-startup-id vigil-ask window --selection','for_window [class="vigil-ask-window"] floating enable']:
    assert value in i3_text,value
bar_cfg=configparser.ConfigParser(interpolation=None,strict=False);bar_cfg.read_string('[top]\n'+bar)
assert bar_cfg['module/vigil-ask']['exec']=='vigil-ask status --follow --polybar' and 'vigil-ask' in bar_cfg['bar/main']['modules-right'].split()
for path in ['bin/lock','bin/vigil-i3-run']:assert 'vigil-ask cancel' in (assets/path).read_text(),f'{path} must stop VIGIL Ask'
assert 'scripts/lib/package-vigil-ask.sh' in (root/'scripts/lib/remix.sh').read_text()
def ask_entry(name):
    entry=configparser.ConfigParser(interpolation=None,strict=False);entry.optionxform=str;entry.read(ask/'system'/name);return entry
app=ask_entry('org.vigilos.Ask.desktop')
assert (app['Desktop Entry']['X-KDE-Shortcuts'],app['Desktop Action selection']['X-KDE-Shortcuts'])==('Meta+Alt+A','Meta+Alt+Shift+A'),'Plasma shortcuts changed'
runner=ask_entry('vigil-ask-krunner.desktop')['Desktop Entry'];activation=ask_entry('org.vigilos.Ask.KRunner.service')['D-BUS Service']
runner_code=(ask/'vigil_ask/krunner.py').read_text()
assert runner['X-Plasma-API']=='DBus2' and runner['X-Plasma-DBusRunner-Service']==activation['Name']=='org.vigilos.Ask.KRunner'
assert f"NAME = '{activation['Name']}'" in runner_code and f"PATH = '{runner['X-Plasma-DBusRunner-Path']}'" in runner_code and activation['Exec']=='/usr/bin/vigil-ask krunner'
menu=ask_entry('vigil-ask-dolphin.desktop')
assert (menu['Desktop Entry']['Type'],menu['Desktop Entry']['MimeType'],menu['Desktop Entry']['X-KDE-Protocols'])==('Service','text/plain;','file')
assert all(menu[f'Desktop Action {name}']['Exec']=='vigil-ask window --file %F' for name in menu['Desktop Entry']['Actions'].strip(';').split(';'))
for installed in ['%{_datadir}/krunner/dbusplugins/org.vigilos.Ask.desktop','%{_datadir}/dbus-1/services/org.vigilos.Ask.KRunner.service',
                  '%{_datadir}/kio/servicemenus/org.vigilos.Ask.desktop']:
    assert installed in spec,installed
if shutil.which('rofi'):
    theme=subprocess.run(['rofi','-theme',ask/'data/vigil-ask.rasi','-dump-theme'],capture_output=True,text=True,timeout=20)
    assert 'Failed to parse' not in theme.stderr and 'accent' in (ask/'data/vigil-ask.rasi').read_text(),theme.stderr
result=subprocess.run([sys.executable,'-B',ask/'tests/test_vigil_ask.py'],capture_output=True,text=True,timeout=180)
assert result.returncode==0,'VIGIL Ask tests failed:\n'+result.stderr[-4000:]
summary=[line for line in result.stderr.splitlines() if line.startswith('Ran ')][-1]+', '+result.stderr.strip().splitlines()[-1]
if 'skipped' in summary:print(f'NOTE: VIGIL Ask {summary}; install python3-pyside6 to run the window tests here')
print('PASS: VIGIL Ask connects to VIGIL GLM accounts only through browser-approved sign-in on chat.vigilglm.ai, asks without tools, ships no Claude Code parts, and keeps its i3 keys, bar and lock stop, and its Plasma shortcuts, KRunner runner and Dolphin menu')

for path in (root/'scripts').rglob('*'):
    if path.is_file() and path.suffix in ['.sh','.py']:
        for ref in re.findall(r'scripts/([\w./-]+\.(?:sh|py))',path.read_text()):
            assert (root/'scripts'/ref).is_file(),f'Broken helper reference {path}: {ref}'
print('PASS: active script references; all checks passed')

for name in ['build-i3-lock.sh','build-guest.sh','remix.sh','install-i3.sh','install-default-apps.sh','package-branding.sh','package-release-common.sh','package-wallpaper-compat.sh','package-vpm.sh','package-vigil-ask.sh','pack-prepared-root.sh','finish-prepared-image.sh','prepare-brand-assets.sh']:
    result=subprocess.run(['bash',root/'scripts/lib'/name],env={**os.environ,'VIGIL_BUILD_GUEST':'0'},capture_output=True,text=True,timeout=10)
    assert result.returncode!=0 and 'approved disposable builder' in result.stderr, f'Broken host guard/helper path: {name}: {result.stderr}'
print('PASS: every internal build entry refuses host execution through its real guard')

for path in (assets/'appearance').rglob('*'):
    if path.is_symlink():
        assert not os.readlink(path).startswith('/home/'),f'Personal theme symlink: {path}'
print('PASS: imported appearance assets have no personal-home symlink targets')

subprocess.run([sys.executable,root/'scripts/lib/test-versioning.py'],check=True)
print('PASS: automatic version allocation, persistence, concurrency, frozen source media and generated product identity')
result=subprocess.run([sys.executable,root/'scripts/lib/prepare-release.py'],env={**os.environ,'VIGIL_BUILD_GUEST':'0'},capture_output=True,text=True,timeout=10)
assert result.returncode!=0 and 'approved disposable builder' in result.stderr
print('PASS: product metadata renderer refuses host execution')
