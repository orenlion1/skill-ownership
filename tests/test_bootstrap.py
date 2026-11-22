"""The repository obeys the principle it publishes: clause first, root files identical."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLAUSE = ('This document routes requests to their owners. Each owner holds its workflow, '
          'guidance, and verification; follow the owner rather than restating or overriding it '
          'here. Everything else here is policy that no owner covers, and where such a policy '
          'limits an owner, the limit holds.')


class BootstrapTests(unittest.TestCase):
    def test_root_files_are_identical_and_open_with_the_clause(self):
        agents = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
        self.assertEqual(agents, (ROOT / 'CLAUDE.md').read_text(encoding='utf-8'))
        preamble = agents.split('\n## ', 1)[0].splitlines()
        self.assertRegex(preamble[0], r'^# \S')
        self.assertEqual(' '.join(' '.join(preamble[1:]).split()), CLAUSE)

    def test_version_is_stable_semver_and_matches_package_metadata(self):
        version = (ROOT / 'VERSION').read_text(encoding='utf-8')
        self.assertRegex(version, r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)\n$')
        package = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))
        self.assertEqual(package['version'], version.strip())
        self.assertIs(package['private'], True)

    def test_every_skill_is_routed_from_the_root_file(self):
        agents = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
        routed = set(re.findall(r'\]\(skills/([a-z0-9-]+)/SKILL\.md\)', agents))
        skills = {p.name for p in (ROOT / 'skills').iterdir() if p.is_dir()}
        self.assertTrue(skills)
        self.assertEqual(routed, skills)


if __name__ == '__main__':
    unittest.main()
