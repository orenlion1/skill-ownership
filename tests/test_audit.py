"""The audit classifies root-file sections and never writes to the target tree."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/skill-ownership/scripts'))
import audit  # noqa: E402
import ownership  # noqa: E402

ROOT_TEXT = """# Repository Policy

Some unrelated opening words.

## Skill routing

| Request | Owning skill |
| --- | --- |
| Alpha work | [Alpha](skills/alpha/SKILL.md) |
| Ghost work | [Ghost](skills/ghost/SKILL.md) |

## Release steps

Releases follow these steps.

- Run the full test suite before tagging.
- Commit the version bump on a release branch.
- Push the branch and open a pull request.
- Verify the merged revision, then tag it.

## Region limits

Regional access is limited to two regions. Work outside them is refused, and that limit
holds for every skill.

## Numbered procedure

1. Open the file.
2. Edit the value.
3. Save and close.
"""
SKILL = ('---\nname: {name}\ndescription: "Does {name} work for a repository. Use when {name} '
         'work is requested."\n---\n\n# {name}\n\n{body}')


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob('*')):
        digest.update(str(path.relative_to(root)).encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


class AuditFixture(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / 'AGENTS.md').write_text(ROOT_TEXT)
        (self.root / 'CLAUDE.md').write_text(ROOT_TEXT + '\nDrift.\n')
        self.add_skill('alpha', '[gone](references/missing.md)\n')
        self.add_skill('beta', 'Nothing routes here.\n')
        self.add_skill('huge', 'x' * (audit.ADVISORY_SKILL_BYTES + 1) + '\n')
        self.report = audit.audit(self.root)

    def add_skill(self, name, body):
        directory = self.root / 'skills' / name
        directory.mkdir(parents=True)
        (directory / 'SKILL.md').write_text(SKILL.format(name=name, body=body))

    def section(self, title):
        return next(s for s in self.report['sections'] if s['title'] == title)

    def test_each_section_gets_exactly_one_class(self):
        self.assertEqual([(s['title'], s['class']) for s in self.report['sections']], [
            ('Skill routing', 'route'),
            ('Release steps', 'workflow'),
            ('Region limits', 'residual-policy'),
            ('Numbered procedure', 'workflow'),
        ])
        self.assertIn('imperative', ' '.join(self.section('Release steps')['signals']))
        self.assertIn('numbered', ' '.join(self.section('Numbered procedure')['signals']))

    def test_routing_gaps_are_listed_in_both_directions(self):
        self.assertEqual(self.report['unrouted_skills'], ['skills/beta', 'skills/huge'])
        self.assertEqual(self.report['routes_without_skill'], ['skills/ghost'])

    def test_clause_identity_oversize_and_links_are_reported(self):
        self.assertFalse(self.report['clause_present'])
        self.assertFalse(self.report['root_files_identical'])
        self.assertEqual([o['skill'] for o in self.report['oversized_skills']], ['skills/huge'])
        self.assertIn('advisory', self.report['oversized_skills'][0]['against'])
        self.assertEqual(len(self.report['broken_links']), 1)
        self.assertIn('references/missing.md', self.report['broken_links'][0])

    def test_recorded_baseline_replaces_the_advisory_threshold(self):
        (self.root / 'policy').mkdir()
        sizes = {f'skills/{n}': (self.root / 'skills' / n / 'SKILL.md').stat().st_size
                 for n in ('alpha', 'beta', 'huge')}
        sizes['skills/alpha'] -= 1
        (self.root / 'policy/skill-size-baseline.json').write_text(
            json.dumps({'schema': 'skill-size-baseline/v1', 'skills': sizes}))
        report = audit.audit(self.root)
        self.assertEqual([o['skill'] for o in report['oversized_skills']], ['skills/alpha'])
        self.assertIn('baseline', report['oversized_skills'][0]['against'])

    def test_audit_never_modifies_the_target_tree(self):
        before = tree_digest(self.root)
        audit.audit(self.root)
        for arguments in (['audit', '--repository', str(self.root)],
                          ['audit', '--repository', str(self.root), '--format', 'json']):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(ownership.main(arguments), 0)
        self.assertEqual(tree_digest(self.root), before)

    def test_markdown_report_names_every_finding_and_json_round_trips(self):
        text = audit.render_markdown(self.report)
        for expected in ('Release steps', 'workflow content that belongs in a skill',
                         'residual policy', 'route', 'skills/beta', 'skills/ghost',
                         'skills/huge', 'references/missing.md', 'proposal'):
            self.assertIn(expected, text)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ownership.main(['audit', '--repository', str(self.root), '--format', 'json'])
        self.assertEqual(json.loads(out.getvalue())['unrouted_skills'],
                         ['skills/beta', 'skills/huge'])

    def test_conforming_repository_reports_no_findings(self):
        clause = audit.CLAUSE
        text = ('# Repository Policy\n\n' + clause + '\n\n## Routing\n\n| Request | Owner |\n'
                '| --- | --- |\n| Alpha | [Alpha](skills/alpha/SKILL.md) |\n\n'
                '## Policy Synchronization\n\nKeep both root files identical.\n')
        for name in ('AGENTS.md', 'CLAUDE.md'):
            (self.root / name).write_text(text)
        for name in ('beta', 'huge'):
            (self.root / 'skills' / name / 'SKILL.md').unlink()
            (self.root / 'skills' / name).rmdir()
        (self.root / 'skills/alpha/SKILL.md').write_text(SKILL.format(name='alpha', body='Fine.\n'))
        report = audit.audit(self.root)
        self.assertTrue(report['clause_present'] and report['root_files_identical'])
        self.assertEqual(audit.finding_count(report), 0)
        self.assertIn('No findings', audit.render_markdown(report))

    def test_repository_without_root_files_fails_clearly(self):
        (self.root / 'AGENTS.md').unlink()
        (self.root / 'CLAUDE.md').unlink()
        with self.assertRaisesRegex(ValueError, 'root file'):
            audit.audit(self.root)


if __name__ == '__main__':
    unittest.main()
