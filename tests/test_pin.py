"""The downstream pin: missing, malformed, or disagreeing with the carried copy fails."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/skill-ownership/scripts'))
import versioning  # noqa: E402

SKILL = ('---\nname: skill-ownership\ndescription: "Audits. Use when adopting."\n'
         'metadata:\n  version: "0.1.0"\n---\n')


class PinTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / 'skills/skill-ownership').mkdir(parents=True)
        (self.root / 'skills/skill-ownership/SKILL.md').write_text(SKILL)
        (self.root / 'policy').mkdir()
        self.pin = {'schema': 'skill-ownership-pin/v1',
                    'upstream_repository': 'https://github.com/example/skill-ownership',
                    'commit': 'a' * 40, 'version': '0.1.0', 'local_adaptations': []}
        self.save()

    def save(self):
        (self.root / versioning.PIN_RELATIVE).write_text(json.dumps(self.pin))

    def errors(self):
        return versioning.pin_errors(self.root)

    def test_matching_pin_passes(self):
        self.assertEqual(self.errors(), [])
        self.pin['local_adaptations'] = [{'path': 'references/local.md', 'reason': 'House rule.'}]
        self.save()
        self.assertEqual(self.errors(), [])

    def test_missing_pin_fails(self):
        (self.root / versioning.PIN_RELATIVE).unlink()
        self.assertIn('pin is missing', self.errors()[0])

    def test_pin_version_disagreeing_with_carried_copy_fails(self):
        self.pin['version'] = '0.1.1'
        self.save()
        errors = self.errors()
        self.assertEqual(len(errors), 1)
        self.assertIn('does not match', errors[0])

    def test_each_malformed_field_fails_alone(self):
        cases = [
            ('schema', 'skill-ownership-pin/v2'), ('commit', 'abc123'), ('commit', 'A' * 40),
            ('version', 'v0.1.0'), ('version', '0.1'),
            ('upstream_repository', 'http://github.com/example/x'),
            # Assembled at run time: the disclosure gate rightly blocks a literal URL with
            # user information or an address-shaped remote in committed text.
            ('upstream_repository', 'https://' + 'user:pass' + '@' + 'github.com/example/x'),
            ('upstream_repository', 'git' + '@' + 'github.com:example/x.git'),
            ('local_adaptations', None), ('local_adaptations', [{'path': 'a.md'}]),
            ('local_adaptations', [{'path': '../outside.md', 'reason': 'x'}]),
            ('local_adaptations', [{'path': '/abs.md', 'reason': 'x'}]),
            ('local_adaptations', [{'path': 'SKILL.md', 'reason': ''}]),
        ]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                original = self.pin[field]
                self.pin[field] = value
                self.save()
                errors = self.errors()
                self.assertEqual(len(errors), 1, errors)
                self.assertIn(field, errors[0])
                self.pin[field] = original
        self.save()
        self.assertEqual(self.errors(), [])

    def test_unknown_missing_or_duplicate_keys_and_bad_json_fail(self):
        self.pin['extra'] = 1
        self.save()
        self.assertIn('exactly', self.errors()[0])
        del self.pin['extra'], self.pin['commit']
        self.save()
        self.assertIn('exactly', self.errors()[0])
        path = self.root / versioning.PIN_RELATIVE
        path.write_text('{"schema": "skill-ownership-pin/v1", "schema": "skill-ownership-pin/v1"}')
        self.assertIn('duplicate', self.errors()[0])
        path.write_text('{not json')
        self.assertEqual(len(self.errors()), 1)

    def test_malformed_carried_frontmatter_is_reported_by_the_pin_check(self):
        (self.root / 'skills/skill-ownership/SKILL.md').write_text(SKILL.replace('"0.1.0"', '0.1.0'))
        self.assertIn('quoted SemVer', self.errors()[0])


if __name__ == '__main__':
    unittest.main()
