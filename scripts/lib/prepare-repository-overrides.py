#!/usr/bin/env python3
"""Bind Fedora repository locations to the base release, independent of product ID.

Use libdnf5's distribution overrides, shared by DNF and PackageKit. Original
Fedora-owned repo files, enabled states and security settings remain untouched.
"""
import configparser
import io
import os
from pathlib import Path
import re
import subprocess
import sys

RELEASE = re.compile(r'\$(?:\{releasever\}|releasever(?![A-Za-z0-9_]))')
LOCATION_OPTIONS = {'name', 'baseurl', 'metalink', 'mirrorlist', 'gpgkey'}


def repository_overrides(sources, base_release='44'):
    if base_release != '44':
        raise ValueError('This product requires the verified Fedora 44 base')
    result = configparser.ConfigParser(interpolation=None)
    seen = set()
    for filename, text in sorted(sources.items()):
        original = configparser.ConfigParser(interpolation=None)
        original.read_string(text, source=filename)
        for repo in original.sections():
            if repo in seen:
                raise ValueError('Duplicate native repository ID: ' + repo)
            seen.add(repo)
            changes = {}
            for key, value in original.items(repo):
                if key in LOCATION_OPTIONS and RELEASE.search(value):
                    changes[key] = RELEASE.sub(base_release, value)
            if changes:
                result[repo] = changes
    for repo in ('fedora', 'updates'):
        if not result.has_option(repo, 'metalink'):
            raise ValueError('Missing native Fedora repository metalink: ' + repo)
    stream = io.StringIO()
    stream.write('# VIGIL OS product versions use the Fedora 44 package base.\n'
                 '# Generated from installed Fedora-owned repository locations.\n'
                 '# Enabled states, TLS and signature checks are inherited unchanged.\n')
    result.write(stream, space_around_delimiters=False)
    return stream.getvalue()


def main():
    if os.environ.get('VIGIL_BUILD_GUEST') != '1' or not Path('/etc/vigilos-disposable-builder').is_file():
        raise SystemExit('ERROR: Run only in the approved disposable builder VM.')
    subprocess.run(['systemd-detect-virt', '--vm', '--quiet'], check=True)
    root, output = map(lambda s: Path(s).resolve(), sys.argv[1:])
    assert (root.parent / '.vigilos-owned').is_file() and root.name == 'squashfs'
    subprocess.run(['chroot', str(root), 'rpm', '-q', '--whatprovides', 'fedora-repos(44)'], check=True)
    subprocess.run(['chroot', str(root), 'rpm', '-V', 'fedora-repos'], check=True)
    files = subprocess.check_output(['chroot', str(root), 'rpm', '-ql', 'fedora-repos'], text=True).splitlines()
    sources = {}
    for name in files:
        path = Path(name)
        if path.parent == Path('/etc/yum.repos.d') and path.suffix == '.repo':
            sources[name] = (root / name.lstrip('/')).read_text()
    output.write_text(repository_overrides(sources))
    print('Prepared Fedora 44 distribution overrides; original signed repository files retained.')


if __name__ == '__main__':
    main()
