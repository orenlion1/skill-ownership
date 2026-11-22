"""Release metadata and local-output exclusion regressions."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('release', ROOT / 'scripts/release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for name in ('VERSION', 'package.json', 'LICENSE'):
            (self.root / name).write_bytes((ROOT / name).read_bytes())
        for skill in sorted((ROOT / 'skills').glob('*/SKILL.md')):
            target = self.root / 'skills' / skill.parent.name
            target.mkdir(parents=True)
            (target / 'SKILL.md').write_bytes(skill.read_bytes())
        self.current, self.package = release.validate(self.root)
        major, minor, patch = release.version_tuple(self.current)
        self.target = f'{major}.{minor}.{patch + 1}'

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for p in sorted(self.root.rglob('*')) if p.is_file()}

    def test_bump_rewrites_every_skill_version_and_only_that_value(self):
        before = self.snapshot()
        release.bump(self.root, self.target)
        after = self.snapshot()
        skills = [name for name in before if name.endswith('SKILL.md')]
        self.assertTrue(skills)
        for name in skills:
            self.assertEqual(after[name], before[name].replace(
                f'version: "{self.current}"'.encode(), f'version: "{self.target}"'.encode()))
            self.assertNotEqual(after[name], before[name])

    def test_skill_version_drift_fails_validation(self):
        skill = next((self.root / 'skills').glob('*/SKILL.md'))
        skill.write_text(skill.read_text().replace(f'"{self.current}"', f'"{self.target}"'))
        with self.assertRaisesRegex(ValueError, 'differs from VERSION'):
            release.validate(self.root)

    def test_repository_metadata_and_license(self):
        release.validate(ROOT)
        text = (ROOT / 'LICENSE').read_text()
        self.assertIn('Permission is hereby granted, free of charge', text)
        self.assertIn('THE SOFTWARE IS PROVIDED "AS IS"', text)

    def test_bump_check_preserves_bytes_then_bump_synchronizes(self):
        before = self.snapshot()
        release.bump(self.root, self.target, check=True)
        self.assertEqual(before, self.snapshot())
        release.bump(self.root, self.target)
        self.assertEqual(self.target, release.validate(self.root, self.target)[0])

    def test_drift_rejects_bump_without_partial_changes(self):
        self.package['version'] = '999.0.0'
        (self.root / 'package.json').write_text(json.dumps(self.package))
        before = self.snapshot()
        with self.assertRaises(ValueError):
            release.bump(self.root, self.target)
        self.assertEqual(before, self.snapshot())

    def test_invalid_versions_and_non_forward_bumps(self):
        for value in ('v1.0.0', '01.0.0', '1.0', '1.0.0-rc.1', '', '1.0.0\n'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                release.bump(self.root, value)
        with self.assertRaises(ValueError):
            release.bump(self.root, self.current)

    def test_tag_must_equal_version(self):
        with self.assertRaises(ValueError):
            release.validate(self.root, self.target)

    def test_tracked_private_outputs_rejected_ignored_files_preserved(self):
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        path = self.root / 'logs/private.txt'
        path.parent.mkdir()
        path.write_text('local evidence')
        release.check_tracked_outputs(self.root)
        subprocess.run(['git', 'add', 'logs/private.txt'], cwd=self.root, check=True)
        with self.assertRaises(ValueError):
            release.check_tracked_outputs(self.root)
        self.assertEqual('local evidence', path.read_text())

    def test_retired_input_documents_cannot_be_reintroduced(self):
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        path = self.root / 'inputs/private-inquiry.md'
        path.parent.mkdir()
        path.write_text('private investigation inquiry')
        release.check_tracked_outputs(self.root)
        subprocess.run(['git', 'add', 'inputs/private-inquiry.md'], cwd=self.root, check=True)
        with self.assertRaises(ValueError):
            release.check_tracked_outputs(self.root)
        self.assertEqual('private investigation inquiry', path.read_text())
