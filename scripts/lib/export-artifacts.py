#!/usr/bin/env python3
"""Describe only finalized run outputs, never private builder keys or disks."""
from pathlib import Path
import hashlib,json,tarfile
if not Path("/etc/vigilos-disposable-builder").is_file():
    raise SystemExit("Disposable builder marker required")
output=Path('/build/output')
isos=list(output.glob('candidate.*/VIGILOS-1.2-*-x86_64.iso'))
if len(isos)!=1:raise SystemExit('Exactly one completed edition ISO required')
iso=isos[0]; edition=iso.name.removeprefix('VIGILOS-1.2-').removesuffix('-x86_64.iso')
evidence=Path('/build/export')/f'VIGILOS-1.2-{edition}-build-evidence.tar.gz'
with tarfile.open(evidence,'w:gz') as archive:
    for name in ['validation.log','branding.log']:
        archive.add(iso.parent/name,arcname=name)
    for path in Path('/build/work').glob('vigilos-branding.*/package-manifest.txt'):
        archive.add(path,arcname='package-manifest.txt')
    if Path('/build-bootstrap.log').is_file():archive.add('/build-bootstrap.log',arcname='builder-bootstrap.log')
records=[]
for path in [iso,evidence]:
    with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    records.append({'name':path.name,'path':str(path),'bytes':path.stat().st_size,'sha256':digest})
print(json.dumps(records))
