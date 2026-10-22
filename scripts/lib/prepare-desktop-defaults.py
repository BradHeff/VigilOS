#!/usr/bin/env python3
"""Product-owned KPackage/XDG defaults; preserve upstream RPM files and licenses."""
from pathlib import Path
import configparser,io,json,os,shutil,subprocess,sys
root,assets=map(lambda s:Path(s).resolve(),sys.argv[1:])
assert os.environ.get('VIGIL_BUILD_GUEST')=='1'
assert Path('/etc/vigilos-disposable-builder').is_file()
assert (root.parent/'.vigilos-owned').is_file() and root.name=='squashfs'
subprocess.run(['systemd-detect-virt','--vm','--quiet'],check=True)
base=root/'usr/share/plasma/look-and-feel'
previews=assets/'plasma-themes/PurPurDay-Global-6/contents/previews'
product=base/'org.vigilos.desktop';(product/'contents').mkdir(parents=True,exist_ok=True)
(product/'metadata.json').write_text(json.dumps({'KPackageStructure':'Plasma/LookAndFeel','KPlugin':{'Id':'org.vigilos.desktop','Name':'VIGIL OS','Description':'VIGIL OS desktop defaults','Version':'1.2','License':'GPL-3.0-only','Authors':[{'Name':'VIGIL OS maintainers'}]}},indent=2)+'\n')
shutil.copy2(assets/'desktop-defaults/defaults',product/'contents/defaults')
shutil.copytree(previews,product/'contents/previews',dirs_exist_ok=True)
def install_launcher_default(package):
 d=package/'contents/plasmoidsetupscripts';d.mkdir(parents=True,exist_ok=True)
 shutil.copy2(Path(__file__).parent.parent/'runtime/vigilos-kickoff-default.js',d/'org.kde.plasma.kickoff.js')
install_launcher_default(product)
# Qt GenericDataLocation searches /usr/local/share ahead of /usr/share. Shadow
# only these compatibility packages, retaining their IDs/authors/licenses and
# ordinary upstream RPM update/verification paths underneath.
overlays=root/'usr/local/share/plasma/look-and-feel'
for suffix,label in [('fedora','VIGIL Classic'),('fedoradark','VIGIL Dark'),('fedoralight','VIGIL Light')]:
 ident=f'org.fedoraproject.{suffix}.desktop';src=base/ident
 assert src.is_dir(),src
 dest=overlays/ident;shutil.copytree(src,dest,dirs_exist_ok=True)
 meta=json.loads((dest/'metadata.json').read_text());meta['KPlugin']['Name']=label
 meta['KPlugin']['Description']='VIGIL OS appearance based on the upstream Plasma theme'
 # Drop translated upstream display names so a locale cannot reintroduce them.
 for key in list(meta['KPlugin']):
  if key.startswith(('Name[','Description[')):del meta['KPlugin'][key]
 (dest/'metadata.json').write_text(json.dumps(meta,indent=2,ensure_ascii=False)+'\n')
 p=dest/'contents/defaults';cfg=configparser.ConfigParser(interpolation=None);cfg.optionxform=str;cfg.read_string(p.read_text())
 cfg['Wallpaper']['Image']='F44'
 group='ksplashrc][KSplash'
 if not cfg.has_section(group):cfg.add_section(group)
 cfg[group]['Theme']='PurPurDay-Splash-6'
 stream=io.StringIO();cfg.write(stream,space_around_delimiters=False);p.write_text(stream.getvalue())
 install_launcher_default(dest)
 old=dest/'contents/previews'
 # These are copies in the product-owned overlay, never upstream originals.
 for f in old.iterdir():
  if f.is_file():f.unlink()
 shutil.copytree(previews,old,dirs_exist_ok=True)
 (dest/'VIGIL-CHANGES.txt').write_text('Product XDG overlay: VIGIL display names, wallpaper defaults and actual VIGIL preview captures. Upstream package IDs, authors, notices and other files retained. Original signed RPM files remain unchanged under /usr/share.\n')
print('Product-owned default and three compatibility theme overlays prepared; upstream core RPM content untouched.')
