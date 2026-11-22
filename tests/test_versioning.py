"""Frontmatter shape and VERSION agreement: each rule fails alone."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/skill-ownership/scripts'))
import versioning  # noqa: E402

FRONTMATTER = ('---\nname: skill-ownership\n'
               'description: "Audits a repository. Use when adopting the contract."\n'
               'metadata:\n  version: "0.1.0"\n---\n\n# Skill Ownership\n')


class FrontmatterShapeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / 'SKILL.md'

    def errors(self, text):
        self.path.write_text(text, encoding='utf-8')
        return versioning.frontmatter_errors(self.path)

    def test_the_documented_shape_passes_and_yields_its_version(self):
        self.assertEqual(self.errors(FRONTMATTER), [])
        self.assertEqual(versioning.declared_version(self.path), '0.1.0')

    def test_each_shape_violation_fails_alone(self):
        cases = {
            'metadata is missing': FRONTMATTER.replace('metadata:\n  version: "0.1.0"\n', ''),
            'key other than version': FRONTMATTER.replace(
                '  version: "0.1.0"\n', '  version: "0.1.0"\n  upstream: "x"\n'),
            'quoted SemVer': FRONTMATTER.replace('"0.1.0"', '0.1.0'),
            'quoted SemVer ': FRONTMATTER.replace('"0.1.0"', "'0.1.0'"),
            'quoted SemVer  ': FRONTMATTER.replace('"0.1.0"', '"0.1"'),
            'quoted SemVer   ': FRONTMATTER.replace('"0.1.0"', '"01.1.0"'),
            'quoted SemVer    ': FRONTMATTER.replace('"0.1.0"', '"0.1.0-rc.1"'),
            'block mapping': FRONTMATTER.replace('metadata:\n  version: "0.1.0"',
                                                 'metadata: {version: "0.1.0"}'),
            'exactly one version': FRONTMATTER.replace(
                '  version: "0.1.0"\n', '  version: "0.1.0"\n  version: "0.1.0"\n'),
            'exactly one version ': FRONTMATTER.replace('  version: "0.1.0"\n', ''),
            'closed frontmatter': FRONTMATTER.replace('---\n\n# Skill', '\n# Skill'),
        }
        for expected, text in cases.items():
            with self.subTest(rule=expected.strip(), text=text):
                errors = self.errors(text)
                self.assertEqual(len(errors), 1, errors)
                self.assertIn(expected.strip(), errors[0])

    def test_missing_or_symlinked_file_fails_closed(self):
        self.assertIn('regular file', versioning.frontmatter_errors(self.path)[0])


class SetVersionTests(unittest.TestCase):
    def test_set_version_changes_the_version_value_and_nothing_else(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'SKILL.md'
            path.write_text(FRONTMATTER, encoding='utf-8')
            versioning.set_version(path, '0.2.0')
            self.assertEqual(path.read_text(encoding='utf-8'),
                             FRONTMATTER.replace('"0.1.0"', '"0.2.0"'))

    def test_set_version_refuses_a_malformed_file_or_target(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'SKILL.md'
            path.write_text(FRONTMATTER.replace('"0.1.0"', '0.1.0'), encoding='utf-8')
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                versioning.set_version(path, '0.2.0')
            path.write_text(FRONTMATTER, encoding='utf-8')
            with self.assertRaises(ValueError):
                versioning.set_version(path, 'v0.2.0')
            self.assertNotEqual(before, b'')


class AgreementTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / 'VERSION').write_text('0.1.0\n')
        for name in ('skill-ownership', 'release-it'):
            (self.root / 'skills' / name).mkdir(parents=True)
            (self.root / 'skills' / name / 'SKILL.md').write_text(
                FRONTMATTER.replace('name: skill-ownership', f'name: {name}'))

    def test_agreeing_tree_passes_and_reports_how_many_skills_it_checked(self):
        self.assertEqual(versioning.agreement_errors(self.root), ([], 2))

    def test_one_skill_disagreeing_with_version_fails(self):
        path = self.root / 'skills/release-it/SKILL.md'
        path.write_text(path.read_text().replace('"0.1.0"', '"0.1.1"'))
        errors, _ = versioning.agreement_errors(self.root)
        self.assertEqual(len(errors), 1)
        self.assertIn('skills/release-it', errors[0])
        self.assertIn("'0.1.1'", errors[0])

    def test_tag_disagreeing_with_version_fails(self):
        errors, _ = versioning.agreement_errors(self.root, tag='0.1.1')
        self.assertEqual(len(errors), 1)
        self.assertIn('tag', errors[0])
        self.assertEqual(versioning.agreement_errors(self.root, tag='0.1.0')[0], [])

    def test_malformed_version_file_or_empty_catalog_fails_closed(self):
        (self.root / 'VERSION').write_text('0.1\n')
        self.assertIn('VERSION', versioning.agreement_errors(self.root)[0][0])
        (self.root / 'VERSION').write_text('0.1.0\n')
        for name in ('skill-ownership', 'release-it'):
            (self.root / 'skills' / name / 'SKILL.md').unlink()
            (self.root / 'skills' / name).rmdir()
        self.assertIn('no skills', versioning.agreement_errors(self.root)[0][0])


if __name__ == '__main__':
    unittest.main()
