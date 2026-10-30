#!/usr/bin/env python3
"""Build VIGIL OS ISOs in disposable guests from verified Fedora inputs."""
from __future__ import annotations
import argparse, datetime, fcntl, hashlib, json, os, re, shlex, shutil
import socket, subprocess, sys, threading, time, urllib.request
from pathlib import Path
sys.dont_write_bytecode = True
from version import BuildLock, preview_release, reserve_release

REPO = Path(__file__).resolve().parents[2]
FEDORA_KEY = '36F612DCF27F7D1A48A835E4DBFCF71C6D9F90A6'
INPUTS = {
    'kde': ('KDE/x86_64/iso', 'Fedora-KDE-Desktop-Live-44-1.7.x86_64.iso',
            'Fedora-KDE-44-1.7-x86_64-CHECKSUM',
            'c8295961d4c41adbf785a31a17c21a971d3b7415fda72dcad0c11c49577bf03a'),
    'cloud': ('Cloud/x86_64/images', 'Fedora-Cloud-Base-Generic-44-1.7.x86_64.qcow2',
              'Fedora-Cloud-44-1.7-x86_64-CHECKSUM',
              '28680fe5b371a5a82ebf43a31926e086a168e59949d03969c5093e7071f90b7f'),
}

def log(message):
    print(f'[{datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}] {message}', flush=True)

def run(args, **kwargs):
    return subprocess.run(list(map(str,args)), check=True, **kwargs)

def sha(path):
    with open(path,'rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

def download(url, target):
    if target.is_file(): return
    log(f'Download {target.name}')
    partial=target.with_name(target.name+'.part')
    run(['curl','--disable','--proto','=https','--proto-redir','=https','--fail','--location','--retry','4','--connect-timeout','30','--output',partial,url])
    partial.replace(target)

def verify_inputs(cache, work, kinds=tuple(INPUTS)):
    """Verify pinned Fedora downloads against signed checksums."""
    cache.mkdir(parents=True,exist_ok=True)
    download('https://fedoraproject.org/fedora.gpg',cache/'fedora.gpg')
    keyhome=work/'keyring'; keyhome.mkdir(mode=0o700)
    paths={}
    for kind in kinds:
        directory,name,checksums,expected=INPUTS[kind]
        base=f'https://download.fedoraproject.org/pub/fedora/linux/releases/44/{directory}'
        download(f'{base}/{name}',cache/name)
        download(f'{base}/{checksums}',cache/checksums)
        result=run(['gpgv','--homedir',keyhome,'--status-fd','1','--keyring',cache/'fedora.gpg',cache/checksums],capture_output=True,text=True)
        (work/f'{kind}-signature.log').write_text(result.stdout+result.stderr)
        if f'VALIDSIG {FEDORA_KEY} ' not in result.stdout:
            raise RuntimeError(f'{kind}: expected Fedora44 signing fingerprint not found')
        signed=(cache/checksums).read_text()
        if f'SHA256 ({name}) = {expected}' not in signed:
            raise RuntimeError(f'{kind}: pinned official checksum differs')
        actual=sha(cache/name)
        if actual != expected: raise RuntimeError(f'{kind}: input SHA256 mismatch')
        log(f'Verified signed input: {name}')
        paths[kind]=cache/name
    return paths

def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0)); return sock.getsockname()[1]

def ssh_args(work, port):
    return ['ssh','-F','/dev/null','-i',str(work/'builder-key'),'-p',str(port),
            '-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=accept-new',
            '-o',f'UserKnownHostsFile={work / "known_hosts"}','-o','ConnectTimeout=8',
            '-o','ServerAliveInterval=15','-o','ServerAliveCountMax=8','builder@127.0.0.1']

def cloud_seed(work, public_key):
    """Create cloud-init media with a temporary builder key."""
    setup=(REPO/'scripts/lib/guest-setup.sh').read_text()
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
  - path: /usr/local/sbin/vigil-bootstrap
    permissions: '0755'
    content: |
'''+''.join('      '+line+'\n' for line in setup.splitlines())+'''
runcmd:
  - [env, VIGIL_DESKTOP=__DESKTOP__, /usr/local/sbin/vigil-bootstrap]
'''
    (work/'user-data').write_text(userdata.replace('__DESKTOP__',work.name))
    (work/'meta-data').write_text(f'instance-id: vigil-{work.name}\nlocal-hostname: vigil-builder\n')
    run(['xorriso','-as','mkisofs','-quiet','-R','-J','-V','cidata','-o',work/'seed.iso',work/'user-data',work/'meta-data'])

def copy_source(work, release_dir):
    """Create read-only source media with frozen release metadata."""
    roots=['scripts','branding','Skel','PLASMA-CONFIGS','kickstarts','LICENSE','LICENSES']
    run(['xorriso','-as','mkisofs','-quiet','-R','-J','-V','VIGIL_SOURCE',
         '-m','__pycache__','-m','*.pyc','-o',work/'source.iso','-graft-points',*[f'{name}={REPO/name}' for name in roots],
         f'version.json={release_dir / "version.json"}', f'release.json={release_dir / "release.json"}'],cwd=REPO)

def stream_build(command, work, qemu, timeout):
    """Record guest output and enforce build timeouts."""
    process=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
    last_output=[time.monotonic()]
    def consume():
        with (work/'build.log').open('w') as logfile:
            for line in process.stdout:
                logfile.write(line); logfile.flush(); last_output[0]=time.monotonic()
                if any(t in line for t in ['===','ERROR:','Verified candidate:','VIGIL_RESULT','Candidate ISO:','Packing EROFS','RPM integrity','i3 desktop installed']):
                    print(line.rstrip(),flush=True)
    reader=threading.Thread(target=consume,daemon=True); reader.start()
    deadline=time.monotonic()+timeout; pulse=time.monotonic()
    while process.poll() is None:
        if qemu.poll() is not None: process.terminate(); raise RuntimeError('Builder VM exited during build')
        if time.monotonic()>deadline: process.terminate(); raise TimeoutError('Build timed out; guest/logs retained')
        if time.monotonic()-pulse>30:
            log(f'Builder active; full log {work / "build.log"}'); pulse=time.monotonic()
        time.sleep(1)
    reader.join()
    if process.returncode: raise RuntimeError(f'Build failed ({process.returncode}); see {work / "build.log"}')

def build_edition(desktop, inputs, args, parent):
    """Build and retrieve one edition in an owned disposable VM."""
    work=parent/desktop; work.mkdir(mode=0o700)
    copy_source(work, parent)
    run(['ssh-keygen','-q','-t','ed25519','-N','','-f',work/'builder-key'])
    cloud_seed(work,(work/'builder-key.pub').read_text())
    run(['qemu-img','create','-q','-f','qcow2','-F','qcow2','-b',inputs['cloud'],work/'builder.qcow2','104G'])
    port=free_port()
    argv=['qemu-system-x86_64','-name',f'vigil-builder-{desktop}','-machine','q35','-accel','kvm','-cpu','host',
          '-m','6144','-smp','4','-display','none','-monitor','none',
          '-drive',f'file={work / "builder.qcow2"},if=virtio,format=qcow2',
          '-device','virtio-scsi-pci,id=scsi0',
          '-drive',f'file={work / "seed.iso"},media=cdrom,readonly=on,format=raw',
          '-drive',f'file={work / "source.iso"},media=cdrom,readonly=on,format=raw',
          '-drive',f'file={inputs["kde"]},media=cdrom,readonly=on,format=raw',
          '-netdev',f'user,id=net0,ipv6=off,hostfwd=tcp:127.0.0.1:{port}-:22','-device','virtio-net-pci,netdev=net0',
          '-serial',f'file:{work / "serial.log"}']
    stderr=(work/'qemu.log').open('w')
    qemu=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=stderr,stderr=stderr)
    (work/'process.json').write_text(json.dumps({'pid':qemu.pid,'port':port,'desktop':desktop,'command':argv},indent=2))
    ssh=ssh_args(work,port)
    try:
        log(f'{desktop}: fresh builder booted, PID {qemu.pid}; waiting for bootstrap')
        deadline=time.monotonic()+args.bootstrap_timeout
        while True:
            if qemu.poll() is not None: raise RuntimeError(f'QEMU failed: {(work/"qemu.log").read_text()}')
            result=subprocess.run(ssh+['test -f /build/ready'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            if result.returncode==0: break
            failure=subprocess.run(ssh+['sudo test -f /build/setup-failed'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            if failure.returncode==0: raise RuntimeError(f'Guest bootstrap failed; inspect {work / "serial.log"}')
            if time.monotonic()>deadline: raise TimeoutError(f'Bootstrap timeout; inspect {work / "serial.log"}')
            time.sleep(10)
        log(f'{desktop}: starting complete build from the verified official ISO')
        remote=f'sudo setsid --wait env VIGIL_BUILD_GUEST=1 VIGIL_DESKTOP={desktop} bash /build/source/scripts/lib/build-guest.sh /dev/disk/by-label/Fedora-KDE-Live-44'
        stream_build(ssh+[remote],work,qemu,args.build_timeout)
        manifest=run(ssh+['sudo python3 /build/source/scripts/lib/export-artifacts.py'],capture_output=True,text=True)
        record=json.loads(manifest.stdout)
        expected={args.release.iso_name(desktop), args.release.evidence_name(desktop)}
        if {entry['name'] for entry in record} != expected or len(record) != 2:
            raise RuntimeError('Builder artifacts do not match the reserved release/edition')
        if any(entry.get('release') != args.release.record() for entry in record):
            raise RuntimeError('Builder release metadata differs from the reserved run snapshot')
        (work/'guest-artifacts.json').write_text(json.dumps(record,indent=2))
        args.output.mkdir(parents=True,exist_ok=True)
        for entry in record:
            target=args.output/entry['name']
            if target.exists(): raise RuntimeError(f'Refusing to overwrite {target}')
            remote_path=shlex.quote(entry['path'])
            with target.with_suffix(target.suffix+'.part').open('wb') as sink:
                run(ssh+[f'sudo cat {remote_path}'],stdin=subprocess.DEVNULL,stdout=sink)
            partial=target.with_suffix(target.suffix+'.part')
            if partial.stat().st_size!=entry['bytes'] or sha(partial)!=entry['sha256']:
                raise RuntimeError(f'Artifact transfer mismatch: {target}')
            partial.replace(target)
            if target.suffix=='.iso':
                target.with_suffix('.iso.sha256').write_text(f'{entry["sha256"]}  {target.name}\n')
        subprocess.run(ssh+['sudo poweroff'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:qemu.wait(timeout=60)
        except subprocess.TimeoutExpired:raise RuntimeError('Builder did not complete clean shutdown')
        log(f'{desktop}: ISO transfer hash verified, builder powered off')
        (work/'SUCCESS.json').write_text(json.dumps({'desktop':desktop,'release':args.release.record(),'artifacts':record,'verified':True},indent=2))
    finally:
        if qemu.poll() is None:
            qemu.terminate()
            try:qemu.wait(timeout=30)
            except subprocess.TimeoutExpired:qemu.kill();qemu.wait()
        stderr.close()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--desktop',choices=['kde','i3','both'],default='both')
    parser.add_argument('--workspace',type=Path,default=REPO/'.build')
    parser.add_argument('--output',type=Path,default=None)
    parser.add_argument('--cache',type=Path,default=None)
    parser.add_argument('--bootstrap-timeout',type=int,default=1800)
    parser.add_argument('--build-timeout',type=int,default=10800)
    parser.add_argument('--check',action='store_true',help='check host prerequisites/source without starting a VM or downloading')
    args=parser.parse_args()
    args.workspace=args.workspace.resolve()
    args.output=args.output.resolve() if args.output else None
    args.cache=(args.cache or args.workspace/'cache').resolve()
    needed=['python3','bash','curl','gpgv','ssh','ssh-keygen','xorriso','qemu-img','qemu-system-x86_64']
    missing=[x for x in needed if not shutil.which(x)]
    if missing:parser.error('Install these host tools first: '+', '.join(missing))
    if not os.access('/dev/kvm',os.R_OK|os.W_OK):parser.error('Existing usable /dev/kvm required; no host permission changes are made')
    run(['bash',REPO/'scripts/validate.sh'])
    upcoming=preview_release(REPO/'version.json')
    if args.check:
        log(f'Host prerequisites and source checks passed; next release {upcoming.version} ({upcoming.codename}); version counter unchanged')
        return

    with BuildLock(REPO) as release_lock:
        build_run(args, release_lock)

def build_run(args, release_lock):
    """Lock the workspace before allocating run state."""
    args.workspace.mkdir(parents=True,exist_ok=True)
    with (args.workspace/'build.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('Another build is active in this workspace; version was not consumed')
        build_locked_workspace(args, release_lock)

def build_locked_workspace(args, release_lock):
    """Reserve one version and finish every requested edition."""
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    parent=args.workspace/f'run-{stamp}';parent.mkdir(mode=0o700)
    args.output=args.output or args.workspace/'output'/stamp
    if args.output.exists() and (not args.output.is_dir() or any(args.output.iterdir())):
        raise RuntimeError('Fresh output directory required; no version was consumed')
    inputs=verify_inputs(args.cache,parent)
    args.release=reserve_release(REPO,parent,stamp,release_lock)
    log(f'Reserved VIGIL OS {args.release.version} ({args.release.codename}) for this run; both editions share this version')
    result={'release':args.release.record(),'desktop':args.desktop,'output':str(args.output),'status':'running'}
    (parent/'RUN.json').write_text(json.dumps(result,indent=2)+'\n')
    try:
        for desktop in (['kde','i3'] if args.desktop=='both' else [args.desktop]):
            build_edition(desktop,inputs,args,parent)
    except BaseException as exc:
        result.update(status='failed',error=str(exc),version_consumed=True)
        (parent/'RUN.json').write_text(json.dumps(result,indent=2)+'\n')
        raise
    result.update(status='complete')
    (parent/'RUN.json').write_text(json.dumps(result,indent=2)+'\n')
    (args.workspace/'LATEST.json').write_text(json.dumps({'output':str(args.output),'evidence':str(parent),'desktop':args.desktop,'release':args.release.record(),'complete':True},indent=2))
    log(f'COMPLETE: verified images in {args.output}; evidence in {parent}')

if __name__=='__main__':
    try:main()
    except (RuntimeError,ValueError,OSError,TimeoutError,subprocess.CalledProcessError) as exc:
        log(f'ERROR: {exc}');sys.exit(1)
