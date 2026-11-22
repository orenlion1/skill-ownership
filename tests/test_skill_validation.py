"""Each skill-validation rule has a fixture that fails for that rule alone."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/skill-ownership/scripts'))
import skill_validation  # noqa: E402

VALID = '---\nname: alpha\ndescription: "Does alpha. Use when alpha is requested."\n---\n\n# Alpha\n'


class SkillValidationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.skill = self.root / 'skills/alpha'
        self.skill.mkdir(parents=True)
        self.write(VALID)

    def write(self, text):
        (self.skill / 'SKILL.md').write_text(text, encoding='utf-8')

    def errors(self):
        return skill_validation.check(self.root)[0]

    def test_valid_catalog_passes_and_counts_what_it_checked(self):
        self.assertEqual(skill_validation.check(self.root), ([], 1))

    def test_each_rule_fails_alone(self):
        cases = {
            'opening YAML frontmatter': '# Alpha\n',
            'closing YAML frontmatter': '---\nname: alpha\n',
            'does not match directory': VALID.replace('name: alpha', 'name: beta'),
            'invalid or missing skill name': VALID.replace('name: alpha', 'name: Alpha_One'),
            'missing description': '---\nname: alpha\n---\n',
            'exceeds 1024 characters': VALID.replace('Does alpha.', 'x' * 1100),
            'angle brackets': VALID.replace('Does alpha.', 'Does <alpha>.'),
            'scaffold placeholder': VALID + '\nTBD\n',
        }
        for expected, text in cases.items():
            with self.subTest(rule=expected):
                self.write(text)
                errors = self.errors()
                self.assertEqual(len(errors), 1, errors)
                self.assertIn(expected, errors[0])

    def test_missing_skill_file_and_symlinked_skill_fail(self):
        (self.skill / 'SKILL.md').unlink()
        self.assertIn('regular non-symlink file', self.errors()[0])
        target = self.root / 'elsewhere'
        target.mkdir()
        (self.root / 'skills/linked').symlink_to(target, target_is_directory=True)
        self.assertTrue(any('real directory' in error for error in self.errors()))

    def test_empty_catalog_fails_rather_than_passing_silently(self):
        (self.skill / 'SKILL.md').unlink()
        self.skill.rmdir()
        errors, count = skill_validation.check(self.root)
        self.assertEqual(count, 0)
        self.assertIn('no skills found', errors[0])


if __name__ == '__main__':
    unittest.main()
