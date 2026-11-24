# Skill Ownership

One owner per rule. A repository's root files (`AGENTS.md`, `CLAUDE.md`) open with the
ownership clause and act as a router: they say which request goes to which skill and keep
only the policy no skill covers. Each skill owns its workflow, guidance, and verification.

> This document routes requests to their owners. Each owner holds its workflow, guidance, and
> verification; follow the owner rather than restating or overriding it here. Everything else
> here is policy that no owner covers, and where such a policy limits an owner, the limit holds.

This repository is the upstream for that principle: the clause, the checks that enforce it,
and the skill that audits a repository and carries the contract by version.

## Layout

| Path | Purpose |
| --- | --- |
| `skills/skill-ownership/` | The skill and everything a downstream repository carries |
| `scripts/` | Repository-only entry points: checks, release metadata, disclosure scans |
| `skill_evals/` | Eval cases, one per skill |
| `policy/` | This repository's own policy files; it obeys its own checks |
| `tests/` | Fixture tests |
| `security/` | Disclosure policy for the publication gates |

## Adopting it

Copy `skills/skill-ownership/` into the adopting repository and record its source version
and commit in `policy/skill-ownership-pin.json`. Then run from that repository's root:

```sh
python3 skills/skill-ownership/scripts/ownership.py audit --repository .   # read-only report
python3 skills/skill-ownership/scripts/ownership.py check --repository .   # every check
```

The [skill](skills/skill-ownership/SKILL.md) holds the workflow.

## Checks

```sh
bash scripts/check.sh              # release metadata, tests, root-file identity
bash scripts/check-disclosure.sh   # secret and institutional-data scans; run before any push
```

## Releases

Ask the coding agent to `run release-it`. [VERSIONING.md](VERSIONING.md) is the release
contract: one `VERSION`, a protected pull request, one annotated tag, exact-SHA CI, and a
curated GitHub Release.

## License

[MIT](LICENSE).
