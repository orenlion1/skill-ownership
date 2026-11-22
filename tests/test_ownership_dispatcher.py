"""The dispatcher runs every check, skips unconfigured optional ones, and fails closed."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPOSITORY_ROOT / 'skills/skill-ownership/scripts'
sys.path.insert(0, str(SCRIPTS))
import ownership  # noqa: E402

CLAUSE = 'This document routes requests to their owners. The limit holds.'
ROOT_TEXT = """# Repository Policy

This document routes requests to their owners.
The limit holds.

## Routing

| Request | Owning skill |
| --- | --- |
| Alpha work | [Alpha](skills/alpha/SKILL.md) |
| Ownership | [Own](skills/skill-ownership/SKILL.md) |

## Policy Synchronization

Keep both files identical.
"""
CARRIED = ('---\nname: skill-ownership\ndescription: "Audits. Use when auditing."\n'
           'metadata:\n  version: "0.1.0"\n---\n')
SKILL = '---\nname: alpha\ndescription: "Does alpha work. Use when alpha is requested."\n---\n\n# Alpha\n'


class DispatcherFixture(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name in ('AGENTS.md', 'CLAUDE.md'):
            (self.root / name).write_text(ROOT_TEXT, encoding='utf-8')
        (self.root / 'skills/alpha').mkdir(parents=True)
        (self.root / 'skills/alpha/SKILL.md').write_text(SKILL, encoding='utf-8')
        (self.root / 'skills/skill-ownership').mkdir()
        (self.root / 'skills/skill-ownership/SKILL.md').write_text(CARRIED, encoding='utf-8')
        (self.root / 'policy').mkdir()
        (self.root / 'policy/skill-ownership-pin.json').write_text(json.dumps({
            'schema': 'skill-ownership-pin/v1',
            'upstream_repository': 'https://github.com/example/skill-ownership',
            'commit': 'a' * 40, 'version': '0.1.0', 'local_adaptations': []}))
        self.policy = {
            'schema': 'root-contract/v1', 'files': ['AGENTS.md', 'CLAUDE.md'], 'max_lines': 50,
            'ownership_clause': CLAUSE,
            'allowed_sections': ['Routing', 'Policy Synchronization'],
            'required_sections': ['Routing', 'Policy Synchronization'],
            'routing_section': 'Routing', 'skills_dir': 'skills',
            'minimum': {'sections': 2, 'skills': 2}}
        self.save()

    def save(self):
        (self.root / 'policy/root-contract.json').write_text(json.dumps(self.policy))

    def run_checks(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ownership.run_checks(self.root)
        return code, out.getvalue(), err.getvalue()

    def test_conforming_repository_passes_and_reports_optional_checks_as_not_configured(self):
        code, out, err = self.run_checks()
        self.assertEqual(code, 0, err)
        self.assertIn('root-contract: 2 root file(s)', out)
        self.assertIn('skill-validation: 2 skill package(s) valid — PASSED', out)
        self.assertIn('frontmatter: metadata.version is a single quoted SemVer — PASSED', out)
        self.assertIn('pin: pin matches the carried copy — PASSED', out)
        for optional in ('docs-contract', 'delegation-contract', 'vendored-imports'):
            self.assertIn(f'{optional}: not configured', out)

    def test_missing_root_contract_fails_because_the_principle_is_always_required(self):
        (self.root / 'policy/root-contract.json').unlink()
        code, out, err = self.run_checks()
        self.assertEqual(code, 1)
        self.assertIn('root-contract: FAILED', out)

    def test_malformed_optional_policy_fails_closed_instead_of_being_skipped(self):
        for name in ('delegation-contract.json', 'vendored-imports.json'):
            with self.subTest(policy=name):
                path = self.root / 'policy' / name
                path.write_text('{not json')
                code, out, err = self.run_checks()
                self.assertEqual(code, 1)
                self.assertIn(name.removesuffix('.json') + ': FAILED', out)
                path.unlink()

    def test_malformed_docs_block_fails_closed(self):
        self.policy['docs'] = {'readme': 'README.md'}
        self.save()
        code, out, err = self.run_checks()
        self.assertEqual(code, 1)
        self.assertIn('docs-contract: FAILED', out)

    def test_every_failing_check_is_reported_in_one_run(self):
        (self.root / 'CLAUDE.md').write_text(ROOT_TEXT + 'drift\n', encoding='utf-8')
        (self.root / 'skills/alpha/SKILL.md').write_text('no frontmatter\n', encoding='utf-8')
        code, out, err = self.run_checks()
        self.assertEqual(code, 1)
        self.assertIn('root-contract: FAILED', out)
        self.assertIn('skill-validation: FAILED', out)
        self.assertIn('not byte-identical', err)

    def test_carried_skill_ownership_copy_needs_no_vendored_import_pin(self):
        imported = self.root / 'skills/imported'
        imported.mkdir()
        (imported / 'SKILL.md').write_text(
            '---\nname: imported\ndescription: "Imports. Use when importing."\n'
            'metadata:\n  version: "1.2.3"\n---\n', encoding='utf-8')
        routed = ROOT_TEXT.replace('## Policy', '| Imp | [Imp](skills/imported/SKILL.md) |\n\n## Policy')
        for name in ('AGENTS.md', 'CLAUDE.md'):
            (self.root / name).write_text(routed, encoding='utf-8')
        (self.root / 'policy/vendored-imports.json').write_text(json.dumps({
            'schema': 'vendored-imports/v1', 'skills': {'skills/imported': {
                'upstream_repository': 'https://github.com/example/upstream',
                'commit': 'a' * 40, 'version': '1.2.3'}}}))
        code, out, err = self.run_checks()
        self.assertEqual(code, 0, err)
        self.assertIn('vendored-imports: 1 imported skill(s) verified', out)

    def test_downstream_run_fails_without_a_pin_or_with_a_disagreeing_one(self):
        pin = self.root / 'policy/skill-ownership-pin.json'
        saved = pin.read_text()
        pin.write_text(saved.replace('0.1.0', '0.1.1'))
        code, out, err = self.run_checks()
        self.assertEqual(code, 1)
        self.assertIn('does not match', err)
        pin.unlink()
        code, out, err = self.run_checks()
        self.assertEqual(code, 1)
        self.assertIn('pin is missing', err)

    def test_carried_frontmatter_with_an_extra_metadata_key_fails(self):
        (self.root / 'skills/skill-ownership/SKILL.md').write_text(
            CARRIED.replace('  version: "0.1.0"\n', '  version: "0.1.0"\n  commit: "abc"\n'))
        code, out, err = self.run_checks()
        self.assertEqual(code, 1)
        self.assertIn('frontmatter: FAILED', out)
        self.assertIn('key other than version', err)

    def test_upstream_run_needs_no_pin_but_requires_version_agreement(self):
        (self.root / 'policy/skill-ownership-pin.json').unlink()
        (self.root / 'VERSION').write_text('0.1.0\n')
        (self.root / 'skills/alpha/SKILL.md').write_text(
            SKILL.replace('---\n\n# Alpha', 'metadata:\n  version: "0.1.0"\n---\n\n# Alpha'))
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ownership.run_checks(self.root, ownership.UPSTREAM_CHECKS)
        self.assertEqual(code, 0, err.getvalue())
        self.assertIn('version-agreement: VERSION agrees with 2 skill(s) — PASSED', out.getvalue())
        (self.root / 'VERSION').write_text('0.2.0\n')
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            self.assertEqual(ownership.run_checks(self.root, ownership.UPSTREAM_CHECKS), 1)


class RealTree(unittest.TestCase):
    def test_this_repository_passes_its_own_checks(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ownership.run_checks(REPOSITORY_ROOT, ownership.UPSTREAM_CHECKS)
        self.assertEqual(code, 0, err.getvalue())

    def test_policy_templates_are_valid_json(self):
        templates = sorted((REPOSITORY_ROOT / 'skills/skill-ownership/templates/policy').glob('*.json'))
        self.assertGreaterEqual(len(templates), 4)
        for template in templates:
            json.loads(template.read_text(encoding='utf-8'))

    def test_root_contract_template_loads_under_the_checker(self):
        import root_contract
        template = REPOSITORY_ROOT / 'skills/skill-ownership/templates/policy/root-contract.json'
        self.assertNotIn('docs', root_contract.load_policy(template))


if __name__ == '__main__':
    unittest.main()
