#!/usr/bin/env python3
"""Brand ISO menu text and load theme after locating the ISO root."""
import pathlib,re,sys
base=pathlib.Path(sys.argv[1])
for rel in ['boot/grub2/grub.cfg','EFI/BOOT/grub.cfg']:
 p=base/rel
 if not p.exists():continue
 s=p.read_text()
 s=s.replace('set default="1"','set default="0"').replace('set timeout=10','set timeout=5')
 # Fedora 44 media define functions inside an if statement; GRUB's parser
 # rejects those declarations (also reproduced by grub2-script-check on base).
 pattern=r'if \[ "\$grub_platform" == "efi" \]; then\n\tfunction load_video \{.*?\nfi\n\nload_video'
 replacement='if [ "$grub_platform" == "efi" ]; then\n  insmod efi_gop\n  insmod efi_uga\n  insmod video_bochs\n  insmod video_cirrus\n  set basicgfx="nomodeset"\nelse\n  set basicgfx="nomodeset vga=791"\nfi\ninsmod all_video'
 s=re.sub(pattern,replacement,s,count=1,flags=re.S)
 s=re.sub(r'\n# VIGIL OS theme, loaded after upstream root detection\n.*?set theme=.*?\n\n','\n',s,flags=re.S)
 s=re.sub(r'^# VIGILOS GRUB Theme\n.*?set theme=.*?\n\n','',s,count=1,flags=re.S)
 lines=s.splitlines()
 for i,line in enumerate(lines):
  if re.match(r'\s*menuentry\s',line):
   line=line.replace('Fedora-KDE-Desktop-Live','VIGIL OS').replace('start VIGIL OS','Start VIGIL OS')
   line=line.replace('--class fedora','--class vigilos')
   lines[i]=line
 s='\n'.join(lines)+'\n'
 m=re.search(r'^\s*menuentry\s',s,re.M)
 if m:
  theme='/boot/grub2/themes/vigilos' if rel.startswith('boot/') else '/EFI/BOOT/themes/vigilos'
  header='\n# VIGIL OS theme, loaded after upstream root detection\ninsmod gfxterm\ninsmod gfxmenu\ninsmod png\nif [ \"$grub_platform\" == \"efi\" ]; then\n  set gfxmode=auto\nelse\n  set gfxmode=1280x800,1024x768,800x600,auto\nfi\n'
  header+=f'loadfont ($root){theme}/unicode.pf2\n'
  for name in ['dejavu_sans_16','dejavu_sans_11','dejavu_sans_bold_16','dejavu_sans_bold_24']:
   header+=f'loadfont ($root){theme}/{name}.pf2\n'
  header+='terminal_output gfxterm\n'+f'set theme=($root){theme}/theme.txt\n\n'
  s=s[:m.start()]+header+s[m.start():]
 p.write_text(s)
