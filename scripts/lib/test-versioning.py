#!/usr/bin/env python3
"""Version reservation/rendering regressions; only temporary fixtures are changed."""
import configparser
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
sys.dont_write_bytecode = True
LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB))
from version import BuildLock, Release, load_config, load_release, preview_release, reserve_release, source_release


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, LIB / file)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


build = module('vigil_build_version_test', 'build.py')
prepare = module('vigil_prepare_release_test', 'prepare-release.py')


class Versioning(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='vigil-version-test-')
        self.base = Path(self.temp.name)
        self.repo = self.base / 'repo'
        self.repo.mkdir()
        self.config = self.repo / 'version.json'
        self.configure()

    def tearDown(self):
        self.temp.cleanup()

    def configure(self, build_number=1, next_version_number=3, codename='Loopback'):
        self.config.write_text(json.dumps(dict(build_number=build_number, next_version_number=next_version_number, codename=codename)))

    def reserve(self, name='run'):
        run = self.base / name
        run.mkdir()
        with BuildLock(self.repo) as lock:
            release = reserve_release(self.repo, run, name, lock)
        return release, run

    def invoke(self, *arguments, edition=None, inputs=None, missing=False):
        with patch.object(build, 'REPO', self.repo), patch.object(build, 'run') as calls, \
             patch.object(build.shutil, 'which', side_effect=lambda n: None if missing else '/fixture/' + n), \
             patch.object(build.os, 'access', return_value=True), \
             patch.object(build, 'verify_inputs', side_effect=inputs or (lambda *a: {})), \
             patch.object(build, 'build_edition', side_effect=edition), \
             patch.object(sys, 'argv', ['build.py', *map(str, arguments)]):
            build.main()
            return calls.call_args_list

    def test_preview_does_not_increment_or_create_lock(self):
        before = self.config.stat().st_mtime_ns, self.config.read_bytes()
        self.assertEqual(preview_release(self.config).version, '1.3')
        self.assertEqual(before, (self.config.stat().st_mtime_ns, self.config.read_bytes()))
        self.assertFalse((self.repo / '.vigil-build.lock').exists())

    def test_check_is_read_only_and_does_not_create_workspace(self):
        work = self.base / 'never-created'
        before = self.config.read_bytes()
        self.invoke('--check', '--workspace', work)
        self.assertEqual(self.config.read_bytes(), before)
        self.assertFalse(work.exists())
        self.assertFalse((self.repo / '.vigil-build.lock').exists())

    def test_reservation_and_frozen_snapshot_survive_build_directory_deletion(self):
        release, run = self.reserve()
        self.assertEqual(release.version, '1.3')
        self.assertEqual(load_release(run / 'release.json'), release)
        self.assertEqual(load_config(self.config)['next_version_number'], 4)
        shutil.rmtree(run)
        self.assertEqual(self.reserve('next')[0].version, '1.4')

    def test_decimal_component_is_integer_not_fraction(self):
        self.configure(next_version_number=9)
        self.assertEqual(self.reserve('nine')[0].version, '1.9')
        ten, _ = self.reserve('ten')
        self.assertEqual(ten.version, '1.10')
        self.assertEqual(ten.iso_name('i3'), 'VIGILOS-1.10-i3-x86_64.iso')
        self.assertEqual(ten.iso_label('kde'), 'VIGILOS-1-10-kde-x86_64')

    def test_manual_build_number_and_codename_and_zero_version(self):
        self.configure(build_number=2, next_version_number=0, codename='New Horizon')
        release, run = self.reserve()
        self.assertEqual(release.version, '2.0')
        self.assertEqual(release.codename_id, 'new-horizon')
        self.assertEqual(load_config(self.config), dict(build_number=2, next_version_number=1, codename='New Horizon'))
        self.configure(build_number=7, next_version_number=8, codename='Later Choice')
        self.assertEqual(source_release(run), release)

    def test_both_editions_share_one_reservation_and_latest_receipt(self):
        seen = []
        def edition(desktop, inputs, args, parent):
            self.assertEqual(source_release(parent), args.release)
            seen.append((desktop, args.release.version, args.release.codename))
        work = self.base / 'both'
        self.invoke('--workspace', work, '--desktop', 'both', edition=edition)
        self.assertEqual(seen, [('kde', '1.3', 'Loopback'), ('i3', '1.3', 'Loopback')])
        self.assertEqual(load_config(self.config)['next_version_number'], 4)
        latest = json.loads((work / 'LATEST.json').read_text())
        self.assertTrue(latest['complete'])
        self.assertEqual(latest['release']['version'], '1.3')
        self.assertEqual(json.loads((Path(latest['evidence']) / 'RUN.json').read_text())['status'], 'complete')

    def test_failed_partial_build_consumes_version_without_false_latest(self):
        work = self.base / 'failed'
        def partial(desktop, inputs, args, parent):
            args.output.mkdir(parents=True, exist_ok=True)
            if desktop == 'i3': raise RuntimeError('Simulated second-edition failure')
            (args.output / args.release.iso_name(desktop)).write_text('temporary test fixture only')
        with self.assertRaisesRegex(RuntimeError, 'second-edition'):
            self.invoke('--workspace', work, edition=partial)
        self.assertFalse((work / 'LATEST.json').exists())
        records = list(work.glob('run-*/RUN.json'))
        self.assertEqual(json.loads(records[0].read_text())['status'], 'failed')
        self.assertEqual(load_config(self.config)['next_version_number'], 4)
        self.assertEqual(len(list(work.glob('output/*/VIGILOS-1.3-kde-x86_64.iso'))), 1)
        seen=[]
        self.invoke('--workspace', self.base/'retry', '--desktop', 'i3', edition=lambda d,i,a,p: seen.append(a.release.version))
        self.assertEqual(seen, ['1.4'])

    def test_input_verification_failure_does_not_consume_version(self):
        before = self.config.read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'signature'):
            self.invoke('--workspace', self.base/'bad-input', inputs=lambda *a: (_ for _ in ()).throw(RuntimeError('signature failure')))
        self.assertEqual(before, self.config.read_bytes())

    def test_nonempty_output_refused_before_reservation(self):
        output=self.base/'existing';output.mkdir();(output/'keep').write_text('existing data')
        with self.assertRaisesRegex(RuntimeError, 'Fresh output'):
            self.invoke('--workspace', self.base/'work', '--output', output)
        self.assertEqual(load_config(self.config)['next_version_number'], 3)
        self.assertEqual((output/'keep').read_text(), 'existing data')

    def test_concurrent_checkout_build_refused_without_consuming(self):
        code='''import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,sys.argv[1])
from version import BuildLock
try:
 with BuildLock(Path(sys.argv[2])): raise SystemExit('Unexpected second lock')
except RuntimeError as e:
 assert 'Another VIGIL build' in str(e)
print('CHECKOUT_LOCK_REFUSAL_PASS')
'''
        with BuildLock(self.repo):
            result=subprocess.run([sys.executable,'-c',code,str(LIB),str(self.repo)],capture_output=True,text=True,check=True,timeout=10)
        self.assertIn('CHECKOUT_LOCK_REFUSAL_PASS',result.stdout)
        self.assertEqual(load_config(self.config)['next_version_number'],3)
        self.assertEqual(self.reserve()[0].version,'1.3')

    def test_shared_workspace_lock_refusal_does_not_consume(self):
        work=self.base/'busy';work.mkdir()
        import fcntl
        with (work/'build.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaisesRegex(RuntimeError,'active in this workspace'):
                self.invoke('--workspace',work)
        self.assertEqual(load_config(self.config)['next_version_number'],3)

    @unittest.skipUnless(shutil.which('xorriso'), 'data ISO tool unavailable')
    def test_actual_source_iso_contains_allocated_metadata(self):
        release,run=self.reserve()
        self.configure(build_number=3,next_version_number=0,codename='Later Manual Edit')
        for name in ['scripts','branding','Skel','PLASMA-CONFIGS','kickstarts']:
            path=self.repo/name;path.mkdir();(path/'fixture.txt').write_text(name)
        (self.repo/'LICENSE').write_text('test fixture')
        work=run/'kde';work.mkdir()
        with patch.object(build,'REPO',self.repo):build.copy_source(work,run)
        extracted=self.base/'extracted-release.json'
        subprocess.run(['xorriso','-osirrox','on','-indev',str(work/'source.iso'),'-extract','/release.json',str(extracted)],check=True,capture_output=True,timeout=15)
        self.assertEqual(load_release(extracted),release)
        self.assertEqual(load_config(self.config)['build_number'],3)

    def test_invalid_configuration_and_snapshot_rejected(self):
        for data in [dict(build_number=True,codename='Loopback',next_version_number=3),dict(build_number=0,codename='Loopback',next_version_number=3),dict(build_number=1,codename='$(false)',next_version_number=3),dict(build_number=1,codename='Loopback',next_version_number=1.3),dict(build_number=1,codename='Loopback',next_version_number=-1)]:
            self.config.write_text(json.dumps(data))
            with self.assertRaises(ValueError): preview_release(self.config)
        self.configure();release,run=self.reserve();data=release.record();data['version']='44';(run/'release.json').write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'integer components'):load_release(run/'release.json')

    def test_source_cd_uses_frozen_metadata_not_live_counter(self):
        release,run=self.reserve();self.configure(build_number=5,codename='Manual Update',next_version_number=0)
        work=run/'kde';work.mkdir()
        with patch.object(build,'REPO',self.repo),patch.object(build,'run') as call:
            build.copy_source(work,run)
        args=call.call_args.args[0]
        self.assertIn(f'release.json={run / "release.json"}',args)
        self.assertIn(f'version.json={run / "version.json"}',args)
        self.assertEqual(load_release(run/'release.json').version,'1.3')

    def test_rendered_identity_and_all_copied_grub_surfaces(self):
        for release in [Release(1,3,'Loopback','qa-13'),Release(1,10,'Loopback','qa-110'),Release(2,0,'New Horizon','qa-20')]:
            for desktop in ['kde','i3']:
                root=self.base/(release.version+'-'+desktop)/'squashfs';(root/'etc/dnf/vars').mkdir(parents=True)
                (root/'etc/dnf/vars/releasever').write_text('44\n')
                (root/'.buildstamp').write_text('[Main]\nProduct=Fedora\nVersion=44\nUUID=preserve-native-uuid\n')
                paths=[root/'boot/grub2/themes/vigilos/theme.txt',root/'usr/share/grub/themes/vigilos/theme.txt',root.parent/'new_iso/EFI/BOOT/themes/vigilos/theme.txt',root.parent/'new_iso/boot/grub2/themes/vigilos/theme.txt']
                for path in paths:path.parent.mkdir(parents=True);path.write_text('text = "VIGIL OS 1.2"\n')
                path=root/'usr/share/sddm/themes/vigilos/metadata.desktop';path.parent.mkdir(parents=True);path.write_text('[SddmGreeterTheme]\nAuthor=Preserved Author\nVersion=1.2\n')
                prepare.prepare_release(root,release,desktop)
                text=(root/'usr/lib/os-release').read_text()
                self.assertIn(f'VERSION_ID={release.version}\n',text);self.assertIn(f'VERSION_CODENAME={release.codename_id}\n',text);self.assertIn(f'BUILD_ID={release.build_id}\n',text)
                self.assertIn(f'VARIANT_ID={desktop}\n',text);self.assertIn(release.codename,(root/'etc/vigilos-release').read_text())
                self.assertEqual((root/'etc/os-release').readlink(),Path('../usr/lib/os-release'))
                self.assertEqual(load_release(root/'usr/lib/vigilos/release.json'),release)
                cfg=configparser.ConfigParser();cfg.read(root/'.buildstamp');self.assertEqual(cfg['Main']['Version'],release.version);self.assertEqual(cfg['Main']['UUID'],'preserve-native-uuid')
                for path in paths:self.assertEqual(path.read_text(),f'text = "VIGIL OS {release.version}"\n')
                self.assertIn('Author=Preserved Author',(root/'usr/share/sddm/themes/vigilos/metadata.desktop').read_text())
                self.assertEqual((root/'etc/dnf/vars/releasever').read_text(),'44\n')

    @unittest.skipUnless(shutil.which('rpmspec'), 'read-only native RPM spec parser unavailable')
    def test_native_rpm_spec_parser_resolves_version_and_dependency(self):
        for script,spec in [('package-branding.sh','vigilos-release-identity.spec'),('package-branding.sh','vigilos-branding.spec'),('install-i3.sh','i3.spec'),('package-wallpaper-compat.sh','vigilos-wallpaper-compat.spec')]:
            text=(LIB/script).read_text();pattern=r'cat >\s*"[^"\n]*/'+re.escape(spec)+r'" <<\x27?SPEC\x27?\n(.*?)\nSPEC'
            match=re.search(pattern,text,re.S);self.assertIsNotNone(match,script)
            body=match[1].replace('$VIGIL_VERSION','1.10').replace('$BASE_EVR','44.0-1.fc44')
            if script=='package-wallpaper-compat.sh':
                tail=text.split("<<'SPEC'",1)[1].split('\nSPEC',1)[0];body+='\n'+tail.lstrip('\n')
            file=self.base/spec;file.write_text(body+'\n')
            for edition in ['0','1']:
                result=subprocess.run(['rpmspec','--parse','--define','vigilos_version 1.10','--define','vigilos_i3 '+edition,str(file)],text=True,capture_output=True,check=True,timeout=10)
                self.assertRegex(result.stdout,r'(?m)^Version:\s+1\.10$')
                if spec=='vigilos-branding.spec':self.assertIn('Requires: vigilos-release-identity = 1.10',result.stdout)


if __name__=='__main__':
    unittest.main(verbosity=2)
