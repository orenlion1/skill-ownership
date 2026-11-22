"""Economization guardrails: each has a fixture that fails when it is violated."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/skill-ownership/scripts'))
import guardrails  # noqa: E402

DESCRIPTION = '"Does alpha work for a repository. Use when alpha work is requested."'
LONG_RULE = ('Always resolve the destination from the explicit user choice first, then the '
             'repository configuration, and only then the default location.')


def skill_text(description=DESCRIPTION, body='# Alpha\n\nShort overview.\n'):
    return f'---\nname: alpha\ndescription: {description}\n---\n\n{body}'


class GuardrailFixture(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.skill = self.root / 'skills/alpha'
        (self.skill / 'references').mkdir(parents=True)
        self.write('SKILL.md', skill_text())
        (self.root / 'policy').mkdir()

    def write(self, relative, text):
        path = self.skill / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path


class SizeRatchetTests(GuardrailFixture):
    def record(self):
        guardrails.record_baseline(self.root)

    def test_unconfigured_ratchet_reports_none_and_recorded_baseline_passes(self):
        self.assertIsNone(guardrails.ratchet_errors(self.root))
        self.record()
        self.assertEqual(guardrails.ratchet_errors(self.root), [])
        baseline = json.loads((self.root / guardrails.BASELINE_RELATIVE).read_text())
        self.assertEqual(baseline['skills']['skills/alpha'],
                         (self.skill / 'SKILL.md').stat().st_size)

    def test_growth_past_the_baseline_fails_and_shrinking_passes(self):
        self.record()
        self.write('SKILL.md', skill_text(body='# Alpha\n\nShort overview.\n\nOne more rule.\n'))
        errors = guardrails.ratchet_errors(self.root)
        self.assertEqual(len(errors), 1)
        self.assertIn('grew', errors[0])
        self.write('SKILL.md', skill_text(body='# Alpha\n'))
        self.assertEqual(guardrails.ratchet_errors(self.root), [])

    def test_unrecorded_skill_and_stale_entry_fail(self):
        self.record()
        (self.root / 'skills/beta').mkdir()
        (self.root / 'skills/beta/SKILL.md').write_text(skill_text().replace('alpha', 'beta'))
        self.assertIn('no recorded baseline', guardrails.ratchet_errors(self.root)[0])
        self.record()
        (self.root / 'skills/beta/SKILL.md').unlink()
        (self.root / 'skills/beta').rmdir()
        self.assertIn('no longer exists', guardrails.ratchet_errors(self.root)[0])

    def test_explicit_record_admits_growth_and_malformed_baseline_fails_closed(self):
        self.record()
        self.write('SKILL.md', skill_text(body='# Alpha\n\nA deliberately longer overview.\n'))
        self.assertTrue(guardrails.ratchet_errors(self.root))
        self.record()
        self.assertEqual(guardrails.ratchet_errors(self.root), [])
        (self.root / guardrails.BASELINE_RELATIVE).write_text('{"schema": "other"}')
        with self.assertRaises(ValueError):
            guardrails.ratchet_errors(self.root)


class DuplicationTests(GuardrailFixture):
    def test_distinct_content_passes(self):
        self.write('references/detail.md', '# Detail\n\nA different, longer explanation that '
                   'only the reference holds and the skill file does not repeat anywhere.\n')
        self.assertEqual(guardrails.duplication_errors(self.root), [])

    def test_rule_stated_in_skill_and_reference_fails(self):
        self.write('SKILL.md', skill_text(body=f'# Alpha\n\n- {LONG_RULE}\n'))
        self.write('references/detail.md', '# Detail\n\n' + LONG_RULE.replace(', then', ',\nthen') + '\n')
        errors = guardrails.duplication_errors(self.root)
        self.assertEqual(len(errors), 1)
        self.assertIn('skills/alpha/SKILL.md', errors[0])
        self.assertIn('references/detail.md', errors[0])

    def test_short_lines_and_fenced_code_are_not_duplication(self):
        block = '```sh\npython3 scripts/tool.py --repository . --format json --verbose --strict --output report.json\n```\n'
        self.write('SKILL.md', skill_text(body=f'# Alpha\n\nRun the checks.\n\n{block}'))
        self.write('references/detail.md', f'# Detail\n\nRun the checks.\n\n{block}')
        self.assertEqual(guardrails.duplication_errors(self.root), [])


class LinkIntegrityTests(GuardrailFixture):
    def test_resolving_links_and_anchors_pass(self):
        self.write('references/detail.md', '# Detail\n\n## Deep Dive: Part 2\n\nText.\n')
        self.write('SKILL.md', skill_text(body=(
            '# Alpha\n\n## Local Section\n\n[d](references/detail.md) '
            '[a](references/detail.md#deep-dive-part-2) [s](#local-section) '
            '[web](https://github.com/example) [mail](mailto:nobody@example.invalid)\n')))
        self.assertEqual(guardrails.link_errors(self.root), [])

    def test_dead_file_link_fails(self):
        self.write('SKILL.md', skill_text(body='# Alpha\n\n[gone](references/missing.md)\n'))
        errors = guardrails.link_errors(self.root)
        self.assertEqual(len(errors), 1)
        self.assertIn('references/missing.md', errors[0])

    def test_dead_anchor_fails_in_another_file_and_in_the_same_file(self):
        self.write('references/detail.md', '# Detail\n\n## Present\n')
        self.write('SKILL.md', skill_text(body=(
            '# Alpha\n\n[x](references/detail.md#absent) [y](#nowhere)\n')))
        errors = guardrails.link_errors(self.root)
        self.assertEqual(len(errors), 2)
        self.assertTrue(any('#absent' in error for error in errors))
        self.assertTrue(any('#nowhere' in error for error in errors))

    def test_link_escaping_the_repository_fails_and_code_is_ignored(self):
        self.write('SKILL.md', skill_text(body=(
            '# Alpha\n\n[out](../../../outside.md)\n\n```md\n[example](not/a/real/file.md)\n```\n'
            '\nInline `[example](also/not/real.md)` stays an example.\n')))
        errors = guardrails.link_errors(self.root)
        self.assertEqual(len(errors), 1)
        self.assertIn('outside.md', errors[0])


class DescriptionShapeTests(GuardrailFixture):
    def errors(self, description):
        self.write('SKILL.md', skill_text(description))
        return guardrails.description_errors(self.root)

    def test_documented_shape_passes_with_either_quote(self):
        self.assertEqual(self.errors(DESCRIPTION), [])
        self.assertEqual(self.errors("'Says \"alpha\" plainly for a repository. Use for alpha requests.'"), [])

    def test_each_violation_fails_alone(self):
        cases = {
            'quoted': DESCRIPTION.strip('"'),
            'between': '"Too short. Use when asked."',
            'between ': '"' + 'Does alpha work. ' * 40 + 'Use when alpha is requested."',
            'trigger': '"Does alpha work for a repository and nothing else at all, every single time."',
            'angle brackets': '"Does <alpha> work for a repository. Use when alpha work is requested."',
            'end with a period': '"Does alpha work for a repository. Use when alpha work is requested"',
            'single line': '>\n  Does alpha work for a repository. Use when alpha work is requested.',
        }
        for expected, description in cases.items():
            with self.subTest(rule=expected.strip()):
                errors = self.errors(description)
                self.assertEqual(len(errors), 1, errors)
                self.assertIn(expected.strip(), errors[0])


class TokenPreservationTests(GuardrailFixture):
    def setUp(self):
        super().setUp()
        self.before = self.skill
        self.write('SKILL.md', skill_text(body=(
            '# Alpha\n\nRun `python3 scripts/tool.py --strict` and wait 30 seconds.\n\n'
            '```sh\nbash scripts/check.sh\n```\n\nSee `policy/alpha.json` for at most 3 rounds.\n')))
        self.after = self.root / 'after/alpha'
        (self.after / 'references').mkdir(parents=True)

    def rewrite(self, skill_body, reference=None):
        (self.after / 'SKILL.md').write_text(skill_text(body=skill_body), encoding='utf-8')
        if reference is not None:
            (self.after / 'references/detail.md').write_text(reference, encoding='utf-8')

    def test_tokens_moved_into_a_reference_are_preserved(self):
        self.rewrite('# Alpha\n\nSee the reference.\n',
                     '# Detail\n\nRun `python3 scripts/tool.py --strict`, wait 30 seconds.\n\n'
                     '```sh\nbash scripts/check.sh\n```\n\n`policy/alpha.json`: 3 rounds.\n')
        self.assertEqual(guardrails.lost_tokens(self.before, self.after), [])

    def test_a_token_lost_in_a_rewrite_fails_and_names_the_token(self):
        self.rewrite('# Alpha\n\nRun `python3 scripts/tool.py --strict` and wait 30 seconds.\n\n'
                     '```sh\nbash scripts/check.sh\n```\n\nSee the policy for a few rounds.\n')
        lost = guardrails.lost_tokens(self.before, self.after)
        self.assertEqual(sorted(lost), ['3 rounds', 'policy/alpha.json'])

    def test_declared_removals_are_honoured_and_unused_declarations_fail(self):
        self.rewrite('# Alpha\n\nRun `python3 scripts/tool.py --strict` and wait 30 seconds.\n\n'
                     '```sh\nbash scripts/check.sh\n```\n\nSee the policy for a few rounds.\n')
        removals = self.root / 'removals.json'
        removals.write_text(json.dumps({'schema': 'token-removals/v1', 'removed': [
            {'token': 'policy/alpha.json', 'reason': 'Policy file retired.'},
            {'token': '3 rounds', 'reason': 'Bound moved to the caller.'}]}))
        self.assertEqual(guardrails.preservation_errors(self.before, self.after, removals), [])
        removals.write_text(json.dumps({'schema': 'token-removals/v1', 'removed': [
            {'token': 'policy/alpha.json', 'reason': 'Policy file retired.'},
            {'token': '3 rounds', 'reason': 'Bound moved to the caller.'},
            {'token': 'never-there', 'reason': 'Stale.'}]}))
        errors = guardrails.preservation_errors(self.before, self.after, removals)
        self.assertEqual(len(errors), 1)
        self.assertIn('never-there', errors[0])

    def test_git_revision_is_compared_with_the_working_tree(self):
        def git(*args):
            subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false',
                            '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                            *args], cwd=self.root, check=True, capture_output=True)
        git('init', '-q')
        git('add', 'skills')
        git('commit', '-q', '-m', 'before')
        self.assertEqual(guardrails.preservation_errors_from_git(self.root, 'HEAD', 'skills/alpha'), [])
        self.write('SKILL.md', skill_text(body='# Alpha\n\nRun `python3 scripts/tool.py --strict`.\n'))
        errors = guardrails.preservation_errors_from_git(self.root, 'HEAD', 'skills/alpha')
        self.assertTrue(any('bash scripts/check.sh' in error for error in errors), errors)
        self.assertTrue(any('30 seconds' in error for error in errors), errors)


if __name__ == '__main__':
    unittest.main()
