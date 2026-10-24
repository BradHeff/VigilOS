#!/usr/bin/env python3
"""Product versions: manually selected build/codename and a persistent run counter."""
from __future__ import annotations
import argparse
from dataclasses import asdict, dataclass
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def integer(value, minimum):
    if type(value) is not int or value < minimum:
        raise ValueError('Build/version numbers must be nonnegative integers; build number starts at1')
    return value


def codename(value):
    if not isinstance(value, str) or len(value) > 64 or not re.fullmatch(r'[A-Za-z][A-Za-z0-9]*(?:[ -][A-Za-z0-9]+)*', value):
        raise ValueError('Codename must use letters, numbers, single spaces or hyphens (maximum64 characters)')
    return value


def read_json(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'Regular version metadata file required: {path}')
    return json.loads(path.read_text())


def load_config(path):
    """Validate the persistent manual release settings and next counter."""
    data = read_json(path)
    if not isinstance(data, dict) or set(data) != {'build_number', 'codename', 'next_version_number'}:
        raise ValueError('version.json requires build_number, codename and next_version_number')
    integer(data['build_number'], 1)
    integer(data['next_version_number'], 0)
    codename(data['codename'])
    return data


@dataclass(frozen=True)
class Release:
    build_number: int
    version_number: int
    codename: str
    build_id: str

    def __post_init__(self):
        integer(self.build_number, 1)
        integer(self.version_number, 0)
        codename(self.codename)
        if not isinstance(self.build_id, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+', self.build_id):
            raise ValueError('Invalid build ID')
        if len(self.iso_label('kde')) > 32:
            raise ValueError('Build/version numbers exceed the32-character ISO label limit')

    @property
    def version(self):
        return f'{self.build_number}.{self.version_number}'

    @property
    def codename_id(self):
        return self.codename.lower().replace(' ', '-')

    def iso_label(self, desktop):
        if desktop not in ('kde', 'i3'):
            raise ValueError('Unknown desktop')
        return f'VIGILOS-{self.build_number}-{self.version_number}-{desktop}-x86_64'

    def iso_name(self, desktop):
        self.iso_label(desktop)
        return f'VIGILOS-{self.version}-{desktop}-x86_64.iso'

    def evidence_name(self, desktop):
        self.iso_label(desktop)
        return f'VIGILOS-{self.version}-{desktop}-build-evidence.tar.gz'

    def record(self):
        return {**asdict(self), 'version': self.version}


def preview_release(config, build_id='preview'):
    data = load_config(config)
    return Release(data['build_number'], data['next_version_number'], data['codename'], build_id)


def load_release(path):
    """Validate a frozen per-run product release."""
    data = read_json(path)
    if not isinstance(data, dict) or set(data) != {'build_number', 'version_number', 'codename', 'build_id', 'version'}:
        raise ValueError('Invalid frozen release metadata')
    release = Release(**{k: data[k] for k in ('build_number', 'version_number', 'codename', 'build_id')})
    if data['version'] != release.version:
        raise ValueError('Frozen release version does not match its integer components')
    return release


def source_release(root=ROOT):
    frozen = Path(root) / 'release.json'
    return load_release(frozen) if frozen.exists() else preview_release(Path(root) / 'version.json')


def atomic_json(path, data, expected=None):
    """Commit JSON atomically without overwriting a concurrent edit."""
    path = Path(path)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    fd, name = tempfile.mkstemp(prefix=f'.{path.name}.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(json.dumps(data, indent=2) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        if expected is not None and path.read_bytes() != expected:
            raise RuntimeError('Version configuration changed during reservation; refusing to overwrite it')
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        if os.path.exists(name): os.unlink(name)


class BuildLock:
    """One builder per checkout, including invocations with different workspaces."""
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.fd = None

    def __enter__(self):
        self.fd = os.open(self.root / '.vigil-build.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(self.fd)
            self.fd = None
            raise RuntimeError('Another VIGIL build is active in this checkout; version was not consumed')
        return self

    def __exit__(self, *args):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


def reserve_release(root, run_dir, build_id, lock):
    """Consume one version under the checkout lock and freeze run metadata."""
    root, run_dir = Path(root).resolve(), Path(run_dir).resolve()
    if lock.root != root or lock.fd is None:
        raise RuntimeError('Checkout build lock required before version reservation')
    config = root / 'version.json'
    before = config.read_bytes()
    data = load_config(config)
    release = Release(data['build_number'], data['next_version_number'], data['codename'], build_id)
    if any((run_dir / n).exists() for n in ('release.json', 'version.json')):
        raise RuntimeError('Fresh release snapshot paths required')
    data['next_version_number'] += 1

    atomic_json(config, data, expected=before)
    for name, payload in [('release.json', release.record()), ('version.json', data)]:
        with (run_dir / name).open('x') as stream:
            stream.write(json.dumps(payload, indent=2) + '\n')
    return release


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fields', action='store_true', help='read-only shell fields from the frozen release or next-version preview')
    args = parser.parse_args()
    release = source_release()
    if args.fields:
        print('\n'.join([release.version, release.codename, release.codename_id, release.build_id]))
    else:
        print(json.dumps(release.record(), indent=2))


if __name__ == '__main__':
    main()
