#!/usr/bin/env python3
"""Run the skill ownership checks for one repository.

One entry point for a repository that carries this skill: `ownership.py check` runs every
check in a fixed order and prints one line per check. A check whose optional policy is
absent reports `not configured`; a policy that is present but unreadable or malformed
fails closed. The root contract is the principle itself, so it is always required.
A downstream repository must also carry a pin that matches its copy of this skill; the
upstream repository runs with `--upstream`, where VERSION agreement takes the pin's place.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import delegation_contract  # noqa: E402
import docs_contract  # noqa: E402
import root_contract  # noqa: E402
import skill_validation  # noqa: E402
import vendored_imports  # noqa: E402
import versioning  # noqa: E402

ROOT_POLICY = 'policy/root-contract.json'
NOT_CONFIGURED = 'not configured'


def check_root_contract(repository: Path) -> tuple[list[str], str]:
    policy = root_contract.load_policy(repository / ROOT_POLICY)
    errors = root_contract.check(repository, policy)
    return errors, f'{len(policy["files"])} root file(s), clause, sections and routing verified'


def check_docs_contract(repository: Path) -> tuple[list[str], str]:
    docs = docs_contract.load_docs_policy(repository / ROOT_POLICY)
    if docs is None:
        return [], NOT_CONFIGURED
    root_file = json.loads((repository / ROOT_POLICY).read_text(encoding='utf-8'))['files'][0]
    return docs_contract.check(repository, docs, root_file), 'diagram sets and README verified'


def check_delegation_contract(repository: Path) -> tuple[list[str], str]:
    policy = repository / delegation_contract.POLICY_RELATIVE
    if not policy.exists():
        return [], NOT_CONFIGURED
    report = delegation_contract.audit(repository, policy)
    errors = [f'{failure.rule} {failure.message}' for failure in report.failures]
    return errors, (f'{report.concepts_checked} concept(s) across '
                    f'{report.callers_checked} caller(s) verified')


def check_vendored_imports(repository: Path) -> tuple[list[str], str]:
    if not (repository / 'policy/vendored-imports.json').exists():
        return [], NOT_CONFIGURED
    return [], f'{vendored_imports.check(repository)} imported skill(s) verified'


def check_skill_validation(repository: Path) -> tuple[list[str], str]:
    skills_dir = 'skills'
    policy = repository / ROOT_POLICY
    if policy.is_file():
        skills_dir = json.loads(policy.read_text(encoding='utf-8')).get('skills_dir', skills_dir)
    errors, count = skill_validation.check(repository, skills_dir)
    return errors, f'{count} skill package(s) valid'


def check_frontmatter(repository: Path) -> tuple[list[str], str]:
    path = repository / versioning.CARRIED_SKILL / 'SKILL.md'
    return versioning.frontmatter_errors(path), 'metadata.version is a single quoted SemVer'


def check_pin(repository: Path) -> tuple[list[str], str]:
    return versioning.pin_errors(repository), 'pin matches the carried copy'


def check_version_agreement(repository: Path) -> tuple[list[str], str]:
    errors, count = versioning.agreement_errors(repository)
    return errors, f'VERSION agrees with {count} skill(s)'


CHECKS = (
    ('root-contract', check_root_contract),
    ('docs-contract', check_docs_contract),
    ('delegation-contract', check_delegation_contract),
    ('vendored-imports', check_vendored_imports),
    ('skill-validation', check_skill_validation),
    ('frontmatter', check_frontmatter),
)
DOWNSTREAM_CHECKS = CHECKS + (('pin', check_pin),)
UPSTREAM_CHECKS = CHECKS + (('version-agreement', check_version_agreement),)


def run_checks(repository: Path, checks=DOWNSTREAM_CHECKS) -> int:
    """Run every check; never stop at the first failure, so one run shows the whole state."""
    failed = 0
    for name, function in checks:
        try:
            errors, summary = function(repository)
        except delegation_contract.PolicyError as error:
            errors, summary = [str(error)], ''
        except (OSError, ValueError, KeyError, TypeError) as error:
            errors, summary = [f'{type(error).__name__}: {error}'], ''
        for error in errors:
            print(f'error: {name}: {error}', file=sys.stderr)
        if errors:
            failed += 1
            print(f'{name}: FAILED ({len(errors)} error(s))')
        elif summary == NOT_CONFIGURED:
            print(f'{name}: not configured')
        else:
            print(f'{name}: {summary} — PASSED')
    return 1 if failed else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    check = commands.add_parser('check', help='run every ownership check')
    check.add_argument('--repository', type=Path, default=Path.cwd())
    check.add_argument('--upstream', action='store_true',
                       help='this is the skill-ownership repository itself: require VERSION '
                            'agreement instead of a downstream pin')
    args = parser.parse_args(argv)
    checks = UPSTREAM_CHECKS if args.upstream else DOWNSTREAM_CHECKS
    return run_checks(args.repository.resolve(), checks)


if __name__ == '__main__':
    sys.exit(main())
