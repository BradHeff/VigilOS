#!/usr/bin/env python3
"""Product-owned KPackage/XDG defaults; preserve upstream RPM files and licenses."""
from pathlib import Path
import configparser,io,json,os,shutil,subprocess,sys
sys.dont_write_bytecode=True
from version import source_release
root,assets=map(lambda s:Path(s).resolve(),sys.argv[1:])
assert os.environ.get('VIGIL_BUILD_GUEST')=='1'
assert Path('/etc/vigilos-disposable-builder').is_file()
assert (root.parent/'.vigilos-owned').is_file() and root.name=='squashfs'
subprocess.run(['systemd-detect-virt','--vm','--quiet'],check=True)
base=root/'usr/share/plasma/look-and-feel'

product=base/'org.vigilos.desktop';(product/'contents').mkdir(parents=True,exist_ok=True)
(product/'metadata.json').write_text(json.dumps({'KPackageStructure':'Plasma/LookAndFeel','KPlugin':{'Id':'org.vigilos.desktop','Name':'VIGIL Dark','Description':'VIGIL OS dark desktop defaults','Version':source_release().version,'License':'GPL-3.0-only','Authors':[{'Name':'VIGIL OS maintainers'}]}},indent=2)+'\n')
shutil.copy2(assets/'desktop-defaults/defaults',product/'contents/defaults')
(product/'contents/previews').mkdir(exist_ok=True)
def install_creation_defaults(package):
 """Install hooks for newly created menus and desktop containments."""
 d=package/'contents/plasmoidsetupscripts';d.mkdir(parents=True,exist_ok=True)
 shutil.copy2(Path(__file__).parent.parent/'runtime/vigilos-kickoff-default.js',d/'org.kde.plasma.kickoff.js')


 shutil.copy2(Path(__file__).parent.parent/'runtime/vigilos-wallpaper-default.js',d/'org.kde.plasma.folder.js')
install_creation_defaults(product)



overlays=root/'usr/local/share/plasma/look-and-feel'
for suffix,label in [('fedora','VIGIL Dark Classic'),('fedoradark','VIGIL Dark'),('fedoralight','VIGIL Dark Compatibility')]:
 ident=f'org.fedoraproject.{suffix}.desktop';src=base/ident
 assert src.is_dir(),src
 dest=overlays/ident;shutil.copytree(src,dest,dirs_exist_ok=True)
 meta=json.loads((dest/'metadata.json').read_text());meta['KPlugin']['Name']=label
 meta['KPlugin']['Description']='VIGIL OS appearance based on the upstream Plasma theme'

 for key in list(meta['KPlugin']):
  if key.startswith(('Name[','Description[')):del meta['KPlugin'][key]
 (dest/'metadata.json').write_text(json.dumps(meta,indent=2,ensure_ascii=False)+'\n')
 p=dest/'contents/defaults';cfg=configparser.ConfigParser(interpolation=None);cfg.optionxform=str;cfg.read_string((assets/'desktop-defaults/defaults').read_text())
 cfg['Wallpaper']['Image']='F44'
 group='ksplashrc][KSplash'
 if not cfg.has_section(group):cfg.add_section(group)
 cfg[group]['Theme']='VIGIL-Dark-Splash'
 stream=io.StringIO();cfg.write(stream,space_around_delimiters=False);p.write_text(stream.getvalue())
 install_creation_defaults(dest)
 old=dest/'contents/previews'

 for f in old.iterdir():
  if f.is_file():f.unlink()

 (dest/'VIGIL-CHANGES.txt').write_text('Product XDG overlay: VIGIL dark defaults and wallpaper. Old previews omitted; authentic captures are retained with acceptance evidence. Upstream package IDs, authors, notices and other files retained. Original signed RPM files remain unchanged under /usr/share.\n')
print('Product-owned default and three compatibility theme overlays prepared; upstream core RPM content untouched.')
