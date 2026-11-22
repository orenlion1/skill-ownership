"""Sync against a local upstream repository standing in for the real one. No network."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/skill-ownership/scripts'))
import sync  # noqa: E402
import versioning  # noqa: E402

CARRIED = 'skills/skill-ownership'
URL = 'https://github.com/example/skill-ownership'


def skill_text(version, body='Body one.\n'):
    return ('---\nname: skill-ownership\ndescription: "Audits a repository. Use when adopting."\n'
            f'metadata:\n  version: "{version}"\n---\n\n# Skill Ownership\n\n{body}')


def git(cwd, *args):
    return subprocess.run(
        ['git', '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false',
         '-c', 'tag.gpgsign=false', '-c', 'user.name=Fixture',
         '-c', 'user.email=fixture@example.invalid', *args],
        cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def digest_outside(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root).as_posix()
        if relative.startswith((CARRIED, '.git/')) or relative in ('.git', versioning.PIN_RELATIVE):
            continue
        digest.update(relative.encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


class SyncFixture(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix='sync-fixture-'))
        self.addCleanup(shutil.rmtree, self.temp, ignore_errors=True)
        self.upstream = self.temp / 'upstream'
        (self.upstream / CARRIED / 'scripts').mkdir(parents=True)
        (self.upstream / CARRIED / 'references').mkdir()
        git(self.temp, 'init', '-q', '-b', 'main', str(self.upstream))
        self.release('0.1.0', {'SKILL.md': skill_text('0.1.0'),
                               'scripts/tool.py': 'print("one")\n',
                               'references/guide.md': '# Guide\n\nUpstream guide one.\n',
                               'references/retired.md': '# Retired\n'})
        (self.upstream / 'unrelated.txt').write_text('not carried\n')
        self.release('0.2.0', {'SKILL.md': skill_text('0.2.0', 'Body two.\n'),
                               'scripts/tool.py': 'print("two")\n',
                               'scripts/new.py': 'print("new")\n',
                               'references/guide.md': '# Guide\n\nUpstream guide two.\n',
                               'references/retired.md': None})
        self.downstream = self.temp / 'downstream'
        (self.downstream / 'policy').mkdir(parents=True)
        (self.downstream / 'README.md').write_text('downstream\n')
        (self.downstream / 'skills/other').mkdir(parents=True)
        (self.downstream / 'skills/other/SKILL.md').write_text('other\n')
        sync.apply(self.downstream, str(self.upstream), '0.1.0', repository_url=URL)

    def release(self, version, files):
        for relative, text in files.items():
            path = self.upstream / CARRIED / relative
            if text is None:
                path.unlink()
            else:
                path.write_text(text)
        git(self.upstream, 'add', '-A')
        git(self.upstream, 'commit', '-q', '-m', f'release {version}')
        git(self.upstream, 'tag', '-a', version, '-m', f'Release {version}')

    def pin(self):
        return json.loads((self.downstream / versioning.PIN_RELATIVE).read_text())

    def carried(self, relative):
        return (self.downstream / CARRIED / relative).read_text()


class AdoptionTests(SyncFixture):
    def test_first_apply_creates_the_carried_copy_and_a_matching_pin(self):
        pin = self.pin()
        self.assertEqual(pin['version'], '0.1.0')
        self.assertEqual(pin['commit'], git(self.upstream, 'rev-parse', '0.1.0^{commit}'))
        self.assertEqual(pin['upstream_repository'], URL)
        self.assertEqual(versioning.pin_errors(self.downstream), [])
        self.assertEqual(pin['local_adaptations'], [])
        self.assertEqual(self.carried('scripts/tool.py'), 'print("one")\n')
        self.assertFalse((self.downstream / 'unrelated.txt').exists())
        self.assertEqual(versioning.declared_version(self.downstream / CARRIED / 'SKILL.md'), '0.1.0')

    def test_first_apply_without_an_upstream_source_is_refused(self):
        empty = self.temp / 'empty'
        empty.mkdir()
        with self.assertRaisesRegex(ValueError, 'upstream'):
            sync.apply(empty, None, None)


class ReportTests(SyncFixture):
    def test_report_is_behind_lists_changes_and_writes_nothing(self):
        before = hashlib.sha256(b''.join(
            p.read_bytes() for p in sorted(self.downstream.rglob('*')) if p.is_file())).hexdigest()
        report = sync.report(self.downstream, str(self.upstream))
        after = hashlib.sha256(b''.join(
            p.read_bytes() for p in sorted(self.downstream.rglob('*')) if p.is_file())).hexdigest()
        self.assertEqual(before, after)
        self.assertEqual((report['current'], report['latest'], report['status']),
                         ('0.1.0', '0.2.0', 'behind'))
        self.assertEqual(report['changed'], [
            'A scripts/new.py', 'D references/retired.md', 'M SKILL.md',
            'M references/guide.md', 'M scripts/tool.py'])
        self.assertEqual(sync.exit_code(report), sync.EXIT_BEHIND)
        self.assertIn('behind', sync.render(report))
        self.assertIn('scripts/new.py', sync.render(report))

    def test_report_is_current_and_clean_at_the_latest_release(self):
        sync.apply(self.downstream, str(self.upstream), None)
        report = sync.report(self.downstream, str(self.upstream))
        self.assertEqual((report['status'], report['changed'], report['drift']), ('current', [], []))
        self.assertEqual(sync.exit_code(report), 0)
        self.assertIn('current', sync.render(report))

    def test_undeclared_local_edit_is_reported_as_drift(self):
        (self.downstream / CARRIED / 'scripts/tool.py').write_text('print("hacked")\n')
        (self.downstream / CARRIED / 'scripts/extra.py').write_text('print("extra")\n')
        report = sync.report(self.downstream, str(self.upstream))
        self.assertEqual(report['drift'], ['scripts/extra.py', 'scripts/tool.py'])
        self.assertEqual(sync.exit_code(report), sync.EXIT_DRIFT)

    def test_pin_commit_that_is_not_the_release_commit_is_an_error(self):
        pin = self.pin()
        pin['commit'] = 'b' * 40
        (self.downstream / versioning.PIN_RELATIVE).write_text(json.dumps(pin))
        with self.assertRaisesRegex(ValueError, 'does not match'):
            sync.report(self.downstream, str(self.upstream))

    def test_only_release_shaped_tags_count(self):
        git(self.upstream, 'tag', 'v9.9.9')
        git(self.upstream, 'tag', 'nightly')
        self.assertEqual(sync.report(self.downstream, str(self.upstream))['latest'], '0.2.0')


class ApplyTests(SyncFixture):
    def test_apply_updates_copy_and_pin_together_and_touches_nothing_else(self):
        outside = digest_outside(self.downstream)
        result = sync.apply(self.downstream, str(self.upstream), None)
        self.assertEqual(digest_outside(self.downstream), outside)
        self.assertEqual(result['to'], '0.2.0')
        self.assertEqual(self.pin()['version'], '0.2.0')
        self.assertEqual(self.pin()['commit'], git(self.upstream, 'rev-parse', '0.2.0^{commit}'))
        self.assertEqual(self.carried('scripts/new.py'), 'print("new")\n')
        self.assertFalse((self.downstream / CARRIED / 'references/retired.md').exists())
        self.assertEqual(versioning.pin_errors(self.downstream), [])

    def test_declared_local_adaptation_is_preserved_and_reported(self):
        local = '# Guide\n\nOur house rule.\n'
        (self.downstream / CARRIED / 'references/guide.md').write_text(local)
        pin = self.pin()
        pin['local_adaptations'] = [{'path': 'references/guide.md', 'reason': 'House rule.'}]
        (self.downstream / versioning.PIN_RELATIVE).write_text(json.dumps(pin))
        self.assertEqual(sync.report(self.downstream, str(self.upstream))['drift'], [])
        result = sync.apply(self.downstream, str(self.upstream), None)
        self.assertEqual(self.carried('references/guide.md'), local)
        self.assertEqual(result['preserved'], ['references/guide.md'])
        self.assertEqual(self.pin()['local_adaptations'], pin['local_adaptations'])
        self.assertEqual(self.carried('scripts/tool.py'), 'print("two")\n')

    def test_adapted_skill_file_keeps_its_text_and_gets_only_the_new_version(self):
        adapted = skill_text('0.1.0', 'Local body.\n')
        (self.downstream / CARRIED / 'SKILL.md').write_text(adapted)
        pin = self.pin()
        pin['local_adaptations'] = [{'path': 'SKILL.md', 'reason': 'Local wording.'}]
        (self.downstream / versioning.PIN_RELATIVE).write_text(json.dumps(pin))
        sync.apply(self.downstream, str(self.upstream), None)
        self.assertEqual(self.carried('SKILL.md'), adapted.replace('"0.1.0"', '"0.2.0"'))
        self.assertEqual(versioning.pin_errors(self.downstream), [])

    def test_apply_refuses_undeclared_drift_and_changes_nothing(self):
        (self.downstream / CARRIED / 'scripts/tool.py').write_text('print("hacked")\n')
        with self.assertRaisesRegex(ValueError, 'undeclared'):
            sync.apply(self.downstream, str(self.upstream), None)
        self.assertEqual(self.pin()['version'], '0.1.0')
        self.assertEqual(self.carried('scripts/tool.py'), 'print("hacked")\n')

    def test_apply_refuses_a_downgrade_and_an_unknown_release(self):
        sync.apply(self.downstream, str(self.upstream), None)
        with self.assertRaisesRegex(ValueError, 'downgrade'):
            sync.apply(self.downstream, str(self.upstream), '0.1.0')
        with self.assertRaisesRegex(ValueError, 'no release'):
            sync.apply(self.downstream, str(self.upstream), '0.9.0')
        self.assertEqual(self.pin()['version'], '0.2.0')

    def test_apply_at_the_current_release_is_a_no_op(self):
        sync.apply(self.downstream, str(self.upstream), None)
        before = (self.downstream / versioning.PIN_RELATIVE).read_bytes()
        result = sync.apply(self.downstream, str(self.upstream), None)
        self.assertEqual(result['changed'], [])
        self.assertEqual((self.downstream / versioning.PIN_RELATIVE).read_bytes(), before)

    def test_symlinked_carried_directory_is_refused(self):
        real = self.temp / 'elsewhere'
        shutil.move(str(self.downstream / CARRIED), real)
        (self.downstream / CARRIED).symlink_to(real, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            sync.apply(self.downstream, str(self.upstream), None)


class CommandTests(SyncFixture):
    def run_main(self, *arguments):
        import contextlib
        import io
        import ownership
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ownership.main(['sync', '--repository', str(self.downstream),
                                   '--upstream', str(self.upstream), *arguments])
        return code, out.getvalue(), err.getvalue()

    def test_report_exit_code_distinguishes_behind_from_current(self):
        code, out, _ = self.run_main()
        self.assertEqual(code, sync.EXIT_BEHIND)
        self.assertIn('status:          behind', out)
        code, out, _ = self.run_main('--apply')
        self.assertEqual(code, 0)
        self.assertIn('0.1.0 -> 0.2.0', out)
        code, out, _ = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn('clean: the carried copy matches its pinned release', out)

    def test_refused_apply_exits_non_zero_with_one_error_line(self):
        (self.downstream / CARRIED / 'scripts/tool.py').write_text('print("hacked")\n')
        code, _, err = self.run_main('--apply')
        self.assertEqual(code, 1)
        self.assertIn('error: sync: refusing to overwrite undeclared local changes', err)


if __name__ == '__main__':
    unittest.main()
