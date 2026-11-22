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
| `tests/` | Fixture tests |
| `security/` | Disclosure policy for the publication gates |

## Checks

```sh
bash scripts/check.sh              # release metadata, tests, root-file identity
bash scripts/check-disclosure.sh   # secret and institutional-data scans; run before any push
```

## License

[MIT](LICENSE).
