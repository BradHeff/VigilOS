#!/usr/bin/env python3
"""Test VIGIL Ask in a disposable Fedora 44 VM: build and install its RPM, run the tests with PySide6, drive the i3 keys,
Rofi and Polybar on a virtual X display, install Claude Code from Anthropic's repository and check setup while signed
out. Nothing is installed on this host."""
from __future__ import annotations
import argparse, datetime, json, os, shutil, subprocess, sys, time
from pathlib import Path
sys.dont_write_bytecode = True
from build import REPO, free_port, log, run, ssh_args, verify_inputs

PHASES = ['package', 'unit', 'i3', 'install', 'signedout', 'system']
BOOTSTRAP = '''#!/bin/bash
set -euo pipefail
exec > >(tee /ask-bootstrap.log /dev/ttyS0) 2>&1
trap 'touch /ask-setup-failed' ERR
systemd-detect-virt --vm --quiet
mkdir -p /mnt/ask-media /ask-test
mount -o ro /dev/disk/by-label/ASK_TEST /mnt/ask-media
cp -a /mnt/ask-media/. /ask-test/
umount /mnt/ask-media
dnf -y install rpm-build python3-pyside6 xdg-utils libnotify polkit desktop-file-utils dejavu-sans-fonts
touch /ask-test/ready
echo ASK_TEST_READY
'''


def stage(media):
    """Sources for rpmbuild plus the test tree, without bytecode."""
    ignore = shutil.ignore_patterns('__pycache__', '*.pyc')
    shutil.copytree(REPO / 'vigil-ask', media / 'source/vigil-ask', ignore=ignore)
    sources = media / 'SOURCES'
    shutil.copytree(REPO / 'vigil-ask', sources / 'vigil-ask', ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'tests'))
    shutil.copy2(REPO / 'branding/logos/source/vigil-mark.svg', sources / 'org.vigilos.Ask.svg')
    shutil.copy2(REPO / 'branding/repos/claude-code.repo', sources)
    shutil.copy2(REPO / 'branding/repos/pki/claude-code.asc', sources)
    shutil.copy2(REPO / 'vigil-ask/vigil-ask.spec', media)
    for name in ('i3', 'polybar', 'rofi'):
        shutil.copytree(REPO / 'branding/i3/skel/.config' / name, media / 'i3/config' / name)
    shutil.copytree(REPO / 'branding/i3/fonts', media / 'i3/fonts', ignore=shutil.ignore_patterns('*LICENSE*'))


def make_seed(work, public_key):
    userdata = '''#cloud-config
users:
  - name: builder
    groups: [wheel]
    shell: /bin/bash
    lock_passwd: true
    sudo: ["ALL=(ALL) NOPASSWD:ALL"]
    ssh_authorized_keys:
      - ''' + public_key.strip() + '''
ssh_pwauth: false
disable_root: true
write_files:
  - path: /usr/local/sbin/ask-test-bootstrap
    permissions: '0755'
    content: |
''' + ''.join('      ' + line + '\n' for line in BOOTSTRAP.splitlines()) + '''
runcmd:
  - [/usr/local/sbin/ask-test-bootstrap]
'''
    (work / 'user-data').write_text(userdata)
    (work / 'meta-data').write_text(f'instance-id: ask-test-{work.name}\nlocal-hostname: ask-test\n')
    run(['xorriso', '-as', 'mkisofs', '-quiet', '-R', '-J', '-V', 'cidata', '-o', work / 'seed.iso', work / 'user-data', work / 'meta-data'])


def boot(work):
    port = free_port()
    argv = ['qemu-system-x86_64', '-name', 'vigil-ask-test', '-machine', 'q35', '-accel', 'kvm', '-cpu', 'host',
            '-m', '4096', '-smp', '2', '-display', 'none', '-monitor', 'none',
            '-drive', f'file={work / "disk.qcow2"},if=virtio,format=qcow2',
            '-drive', f'file={work / "seed.iso"},media=cdrom,readonly=on,format=raw',
            '-drive', f'file={work / "ask-test.iso"},media=cdrom,readonly=on,format=raw',
            '-netdev', f'user,id=net0,ipv6=off,hostfwd=tcp:127.0.0.1:{port}-:22', '-device', 'virtio-net-pci,netdev=net0',
            '-serial', f'file:{work / "serial.log"}']
    with (work / 'qemu.log').open('w') as qemu_log:
        qemu = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=qemu_log, stderr=qemu_log)
    return qemu, ssh_args(work, port)


def quiet(ssh, command):
    return subprocess.run(ssh + [command], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def wait_ready(qemu, ssh, work, timeout):
    deadline = time.monotonic() + timeout
    while not quiet(ssh, 'test -f /ask-test/ready'):
        if qemu.poll() is not None:
            raise RuntimeError(f'QEMU exited; see {work / "qemu.log"}')
        if quiet(ssh, 'test -f /ask-setup-failed'):
            raise RuntimeError(f'Guest setup failed; see {work / "serial.log"}')
        if time.monotonic() > deadline:
            raise TimeoutError(f'Guest not ready; see {work / "serial.log"}')
        time.sleep(5)


def guest(ssh, command, work, checks):
    result = subprocess.run(ssh + [command], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=1800)
    with (work / 'guest.log').open('a') as record:
        record.write(f'$ {command}\n{result.stdout}{result.stderr}[exit {result.returncode}]\n\n')
    for line in result.stdout.splitlines():
        if line.startswith(('PASS: ', 'FAIL: ')):
            print(line, flush=True)
            checks.append(line)
    return result


def fetch(ssh, work):
    """Copy the guest's check log and screenshots into the evidence folder."""
    listing = subprocess.run(ssh + ['ls out'], stdin=subprocess.DEVNULL, capture_output=True, text=True)
    for name in listing.stdout.split():
        if name.endswith(('.png', '.log')):
            with (work / name).open('wb') as sink:
                subprocess.run(ssh + [f'cat out/{name}'], stdin=subprocess.DEVNULL, stdout=sink)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--workspace', type=Path, default=REPO / '.build')
    parser.add_argument('--cache', type=Path, default=None)
    parser.add_argument('--boot-timeout', type=int, default=1200)
    args = parser.parse_args()
    needed = ['curl', 'gpgv', 'ssh', 'ssh-keygen', 'xorriso', 'qemu-img', 'qemu-system-x86_64']
    missing = [x for x in needed if not shutil.which(x)]
    if missing:
        parser.error('Install these host tools first: ' + ', '.join(missing))
    if not os.access('/dev/kvm', os.R_OK | os.W_OK):
        parser.error('Existing usable /dev/kvm required; no host permission changes are made')
    workspace = args.workspace.resolve()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    work = workspace / 'vigil-ask-test' / f'run-{stamp}'
    work.mkdir(parents=True, mode=0o700)
    image = verify_inputs((args.cache or workspace / 'cache').resolve(), work, kinds=['cloud'])['cloud']
    stage(work / 'media')
    run(['xorriso', '-as', 'mkisofs', '-quiet', '-R', '-J', '-V', 'ASK_TEST', '-m', '__pycache__', '-o', work / 'ask-test.iso', work / 'media'])
    run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', work / 'builder-key'])
    make_seed(work, (work / 'builder-key.pub').read_text())
    run(['qemu-img', 'create', '-q', '-f', 'qcow2', '-F', 'qcow2', '-b', image, work / 'disk.qcow2', '20G'])
    commit = subprocess.run(['git', '-C', REPO, 'describe', '--always', '--dirty'], capture_output=True, text=True).stdout.strip()
    result = {'started': stamp, 'source': commit, 'image': image.name, 'checks': [], 'status': 'running'}
    checks = result['checks']
    qemu = ssh = None
    try:
        qemu, ssh = boot(work)
        log(f'Test VM booted, PID {qemu.pid}; waiting for setup')
        wait_ready(qemu, ssh, work, args.boot_timeout)
        facts = guest(ssh, 'uname -r; getenforce; rpm -q python3-pyside6 selinux-policy-targeted', work, checks)
        result['guest'] = facts.stdout.split()
        for phase in PHASES:
            log(f'Phase: {phase}')
            guest(ssh, f'bash /ask-test/source/vigil-ask/tests/vm-checks.sh {phase}', work, checks)
        result['claude_code'] = guest(ssh, 'rpm -q claude-code', work, []).stdout.strip()
        fetch(ssh, work)
    except BaseException as exc:
        result.update(status='error', error=str(exc))
        raise
    finally:
        if qemu:
            if ssh and qemu.poll() is None:
                quiet(ssh, 'sudo poweroff')
                try:
                    qemu.wait(timeout=90)
                except subprocess.TimeoutExpired:
                    pass
            if qemu.poll() is None:
                qemu.kill()
                qemu.wait()
        failed = [c for c in checks if c.startswith('FAIL')]
        if result['status'] == 'running':
            result['status'] = 'passed' if checks and not failed else 'failed'
        (work / 'RESULT.json').write_text(json.dumps(result, indent=2) + '\n')
        log(f'{len(checks) - len(failed)} checks passed, {len(failed)} failed; evidence in {work}')
    if result['status'] != 'passed':
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, OSError, TimeoutError, subprocess.CalledProcessError) as exc:
        log(f'ERROR: {exc}')
        sys.exit(1)
