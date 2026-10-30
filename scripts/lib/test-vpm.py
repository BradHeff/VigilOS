#!/usr/bin/env python3
"""Test VpM as root in a disposable Fedora 44 VM, including power cuts. Nothing is installed on this host."""
from __future__ import annotations
import argparse, datetime, json, os, shutil, subprocess, sys, time
from pathlib import Path
sys.dont_write_bytecode = True
from build import REPO, free_port, log, run, ssh_args, verify_inputs

POINTS = ['staging:1', 'committing:1', 'recorded:0', 'cleanup:1', 'finished:0', 'removing:1', 'removed:0']
RECIPES = ['vmtest-hello-1', 'vmtest-hello-2', 'vmtest-scripted', 'vmtest-failing']
BOOTSTRAP = '''#!/bin/bash
set -euo pipefail
exec > >(tee /vpm-bootstrap.log /dev/ttyS0) 2>&1
trap 'touch /vpm-setup-failed' ERR
systemd-detect-virt --vm --quiet
touch /etc/vpm-system-test-vm
mkdir -p /mnt/vpm-media /vpm-test
mount -o ro /dev/disk/by-label/VPM_TEST /mnt/vpm-media
cp -a /mnt/vpm-media/. /vpm-test/
umount /mnt/vpm-media
install -m 0755 /vpm-test/bin/vpm /usr/local/bin/vpm
command -v matchpathcon >/dev/null || dnf -y install libselinux-utils
touch /vpm-test/ready
echo VPM_TEST_READY
'''

def build_vpm(source, media, work):
    with (work/'vpm-build.log').open('w') as output:
        run(['cargo','build','--release','--locked','--manifest-path',source/'Cargo.toml'],stdout=output,stderr=output)
    target=source/'target/release'
    (media/'bin').mkdir(parents=True)
    shutil.copy2(target/'vpm',media/'bin/vpm')
    run([target/'vpm','key','generate','--no-passphrase','--comment','VpM VM test (throwaway)',work/'test-key'],stdout=subprocess.DEVNULL)
    (media/'keys').mkdir()
    shutil.copy2(work/'test-key.pub',media/'keys/test.pub')
    packages=media/'packages'
    (packages/'unsigned').mkdir(parents=True)
    env={**os.environ,'SOURCE_DATE_EPOCH':'1700000000'}
    with (work/'packages.log').open('w') as output:
        for name in RECIPES:
            recipe=work/'recipes'/name
            shutil.copytree(source/'tests/system/recipes'/name,recipe)
            run([target/'vpm-build','-C',recipe,'--out',packages,'--sign',work/'test-key.key'],env=env,stdout=output,stderr=output)
        run([target/'vpm-build','-C',work/'recipes/vmtest-scripted','--out',packages/'unsigned','--force'],env=env,stdout=output,stderr=output)
    shutil.copy2(source/'tests/system/system-test.sh',media/'system-test.sh')
    run(['xorriso','-as','mkisofs','-quiet','-R','-J','-V','VPM_TEST','-o',work/'vpm-test.iso',media])

def make_seed(work, public_key):
    userdata='''#cloud-config
users:
  - name: builder
    groups: [wheel]
    shell: /bin/bash
    lock_passwd: true
    sudo: ["ALL=(ALL) NOPASSWD:ALL"]
    ssh_authorized_keys:
      - '''+public_key.strip()+'''
ssh_pwauth: false
disable_root: true
write_files:
  - path: /usr/local/sbin/vpm-test-bootstrap
    permissions: '0755'
    content: |
'''+''.join('      '+line+'\n' for line in BOOTSTRAP.splitlines())+'''
runcmd:
  - [/usr/local/sbin/vpm-test-bootstrap]
'''
    (work/'user-data').write_text(userdata)
    (work/'meta-data').write_text(f'instance-id: vpm-test-{work.name}\nlocal-hostname: vpm-test\n')
    run(['xorriso','-as','mkisofs','-quiet','-R','-J','-V','cidata','-o',work/'seed.iso',work/'user-data',work/'meta-data'])

def boot(work, name):
    port=free_port()
    argv=['qemu-system-x86_64','-name',f'vpm-test-{name}','-machine','q35','-accel','kvm','-cpu','host',
          '-m','2048','-smp','2','-display','none','-monitor','none',
          '-drive',f'file={work / "disk.qcow2"},if=virtio,format=qcow2',
          '-drive',f'file={work / "seed.iso"},media=cdrom,readonly=on,format=raw',
          '-drive',f'file={work / "vpm-test.iso"},media=cdrom,readonly=on,format=raw',
          '-netdev',f'user,id=net0,ipv6=off,hostfwd=tcp:127.0.0.1:{port}-:22','-device','virtio-net-pci,netdev=net0',
          '-serial',f'file:{work / f"serial-{name}.log"}']
    qemu_log=(work/f'qemu-{name}.log').open('w')
    qemu=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=qemu_log,stderr=qemu_log)
    qemu_log.close()
    return qemu,ssh_args(work,port)

def wait_ready(qemu, ssh, work, name, timeout):
    deadline=time.monotonic()+timeout
    while True:
        if qemu.poll() is not None: raise RuntimeError(f'QEMU exited; see {work / f"qemu-{name}.log"}')
        quiet={'stdin':subprocess.DEVNULL,'stdout':subprocess.DEVNULL,'stderr':subprocess.DEVNULL}
        if subprocess.run(ssh+['test -f /vpm-test/ready'],**quiet).returncode==0: return
        if subprocess.run(ssh+['test -f /vpm-setup-failed'],**quiet).returncode==0:
            raise RuntimeError(f'Guest setup failed; see {work / f"serial-{name}.log"}')
        if time.monotonic()>deadline: raise TimeoutError(f'Guest not ready; see {work / f"serial-{name}.log"}')
        time.sleep(5)

def guest(ssh, command, work, checks):
    result=subprocess.run(ssh+[command],stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=1800)
    with (work/'guest.log').open('a') as record:
        record.write(f'$ {command}\n{result.stdout}{result.stderr}[exit {result.returncode}]\n\n')
    for line in result.stdout.splitlines():
        if line.startswith(('PASS: ','FAIL: ')):
            print(line,flush=True)
            checks.append(line)
    return result

def stop(qemu, ssh=None):
    if ssh and qemu.poll() is None:
        subprocess.run(ssh+['sudo poweroff'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try: qemu.wait(timeout=90); return
        except subprocess.TimeoutExpired: pass
    if qemu.poll() is None: qemu.kill(); qemu.wait()

def main():
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--vpm',type=Path,default=REPO.parent/'VpM',help='VpM source repository (default: ../VpM)')
    parser.add_argument('--workspace',type=Path,default=REPO/'.build')
    parser.add_argument('--cache',type=Path,default=None)
    parser.add_argument('--points',default=','.join(POINTS),help='power-cut points, comma-separated; empty for none')
    parser.add_argument('--boot-timeout',type=int,default=900)
    args=parser.parse_args()
    source=args.vpm.resolve()
    if not (source/'Cargo.toml').is_file() or not (source/'tests/system/system-test.sh').is_file():
        parser.error(f'{source} is not a VpM source repository')
    needed=['cargo','curl','gpgv','ssh','ssh-keygen','xorriso','qemu-img','qemu-system-x86_64']
    missing=[x for x in needed if not shutil.which(x)]
    if missing: parser.error('Install these host tools first: '+', '.join(missing))
    if not os.access('/dev/kvm',os.R_OK|os.W_OK): parser.error('Existing usable /dev/kvm required; no host permission changes are made')
    points=[p for p in args.points.split(',') if p]
    unknown=[p for p in points if p not in POINTS]
    if unknown: parser.error(f'Unknown power-cut points {unknown}; choose from {POINTS}')

    workspace=args.workspace.resolve()
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    work=workspace/'vpm-test'/f'run-{stamp}'
    work.mkdir(parents=True,mode=0o700)
    cache=(args.cache or workspace/'cache').resolve()
    image=verify_inputs(cache,work,kinds=['cloud'])['cloud']
    commit=subprocess.run(['git','-C',source,'describe','--always','--dirty'],capture_output=True,text=True).stdout.strip()
    result={'started':stamp,'vpm_source':str(source),'vpm_commit':commit,'image':image.name,'points':points,'checks':[],'status':'running'}
    log(f'Building VpM {commit} and its test packages')
    build_vpm(source,work/'media',work)
    run(['ssh-keygen','-q','-t','ed25519','-N','','-f',work/'builder-key'])
    make_seed(work,(work/'builder-key.pub').read_text())
    run(['qemu-img','create','-q','-f','qcow2','-F','qcow2','-b',image,work/'disk.qcow2','20G'])
    checks=result['checks']
    qemu=None
    try:
        qemu,ssh=boot(work,'boot0')
        log(f'Test VM booted, PID {qemu.pid}; waiting for setup')
        wait_ready(qemu,ssh,work,'boot0',args.boot_timeout)
        facts=guest(ssh,'uname -r; getenforce; rpm -q selinux-policy-targeted systemd sqlite-libs; findmnt -no FSTYPE /',work,checks)
        result['guest']=facts.stdout.split()
        log('Running the VpM system tests as root on the running system')
        guest(ssh,'sudo bash /vpm-test/system-test.sh run',work,checks)
        for number,point in enumerate(points,1):
            started=guest(ssh,f'sudo bash /vpm-test/system-test.sh powercut-start {point}',work,checks)
            if 'PAUSED' not in started.stdout:
                checks.append(f'FAIL: power cut at {point}: the transaction did not reach the point')
                print(checks[-1],flush=True)
                continue
            qemu.kill(); qemu.wait()
            log(f'Power cut at {point}: VM killed mid-transaction; booting again')
            qemu,ssh=boot(work,f'boot{number}')
            wait_ready(qemu,ssh,work,f'boot{number}',args.boot_timeout)
            guest(ssh,f'sudo bash /vpm-test/system-test.sh powercut-check {point}',work,checks)
        stop(qemu,ssh)
    except BaseException as exc:
        result.update(status='error',error=str(exc))
        raise
    finally:
        if qemu: stop(qemu)
        failed=[c for c in checks if c.startswith('FAIL')]
        if result['status']=='running': result['status']='passed' if checks and not failed else 'failed'
        (work/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
        log(f'{len(checks)-len(failed)} checks passed, {len(failed)} failed; evidence in {work}')
    if result['status']!='passed': sys.exit(1)

if __name__=='__main__':
    try:main()
    except (RuntimeError,ValueError,OSError,TimeoutError,subprocess.CalledProcessError) as exc:
        log(f'ERROR: {exc}');sys.exit(1)
