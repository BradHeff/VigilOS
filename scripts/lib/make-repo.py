#!/usr/bin/env python3
"""Sign the product RPMs from VIGIL OS builds and add them to a per-edition DNF repository. Run it where the signing key
lives; it uploads nothing. A package version already in the repository is kept and never replaced."""
from __future__ import annotations
import argparse, re, shutil, subprocess, sys, tarfile, tempfile
from pathlib import Path
sys.dont_write_bytecode = True
from build import REPO_PACKAGES, log

BUNDLE = re.compile(r'VIGILOS-[0-9]+\.[0-9]+-(kde|i3)-rpms\.tar')


def bundles(outputs):
    """Each build's exported RPM bundle with its edition."""
    found = []
    for output in outputs:
        found += [(path, BUNDLE.fullmatch(path.name)[1]) for path in sorted(output.glob('VIGILOS-*-rpms.tar')) if BUNDLE.fullmatch(path.name)]
    return found


def query(path, tag):
    return subprocess.run(['rpm', '-qp', '--nosignature', '--qf', tag, path], capture_output=True, text=True, check=True).stdout


def publish(bundle, edition, repo, key, work):
    """Copy the bundle's publishable RPMs into the edition's Packages folder, signing each new one."""
    packages = repo / '44' / edition / 'Packages'
    packages.mkdir(parents=True, exist_ok=True)
    unpacked = work / bundle.stem
    with tarfile.open(bundle) as archive:
        archive.extractall(unpacked, filter='data')
    added, kept = [], []
    for rpm in sorted(unpacked.glob('*.rpm')):
        if query(rpm, '%{NAME}') not in REPO_PACKAGES:
            continue
        target = packages / rpm.name
        if target.exists():
            kept.append(rpm.name)
            continue
        shutil.copy2(rpm, target.with_suffix('.part'))
        subprocess.run(['rpmsign', '--define', f'_gpg_name {key}', '--addsign', target.with_suffix('.part')], check=True,
                       stdout=subprocess.DEVNULL)
        target.with_suffix('.part').replace(target)
        added.append(rpm.name)
    return added, kept


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('outputs', nargs='+', type=Path, help='build output folders, such as .build/output/<timestamp>')
    parser.add_argument('--repo', type=Path, required=True, help='the repository folder to add to; publish its contents as they are')
    parser.add_argument('--key', required=True, help='GnuPG key ID or fingerprint that signs the packages and metadata')
    args = parser.parse_args()
    missing = [tool for tool in ('rpm', 'rpmsign', 'createrepo_c', 'gpg') if not shutil.which(tool)]
    if missing:
        parser.error('Install these tools first: ' + ', '.join(missing))
    if subprocess.run(['gpg', '--batch', '--list-secret-keys', args.key], capture_output=True).returncode:
        parser.error(f'No secret key {args.key} in this GnuPG keyring')
    found = bundles(args.outputs)
    if not found:
        parser.error('No VIGILOS-*-rpms.tar bundles in those folders; builds from before 1.11 did not export their RPMs')
    repo = args.repo.resolve()
    editions = set()
    with tempfile.TemporaryDirectory(prefix='vigil-make-repo-') as work:
        for bundle, edition in found:
            added, kept = publish(bundle, edition, repo, args.key, Path(work))
            editions.add(edition)
            log(f'{bundle.name}: {len(added)} signed and added, {len(kept)} already published and kept')
    for edition in sorted(editions):
        folder = repo / '44' / edition
        subprocess.run(['createrepo_c', '--quiet', '--update', folder], check=True)
        metadata = folder / 'repodata/repomd.xml'
        subprocess.run(['gpg', '--batch', '--yes', '--local-user', args.key, '--armor', '--detach-sign', '--output',
                        metadata.with_suffix('.xml.asc'), metadata], check=True)
        log(f'{folder}: metadata rebuilt and signed')
    exported = subprocess.run(['gpg', '--batch', '--armor', '--export', args.key], capture_output=True, check=True).stdout
    (repo / 'RPM-GPG-KEY-vigilos').write_bytes(exported)
    log(f'Public key written to {repo / "RPM-GPG-KEY-vigilos"}; build with --repo-key pointing at it')


if __name__ == '__main__':
    try:
        main()
    except (OSError, subprocess.CalledProcessError, tarfile.TarError) as exc:
        log(f'ERROR: {exc}')
        sys.exit(1)
