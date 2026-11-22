# Repository Policy

This document routes requests to their owners. Each owner holds its workflow, guidance,
and verification; follow the owner rather than restating or overriding it here. Everything
else here is policy that no owner covers, and where such a policy limits an owner, the limit
holds.

## Routing

| Request or situation | Owning skill |
| --- | --- |
| Auditing a repository against the skill ownership principle, refactoring it toward a routing table with one owner per rule, checking the contract, or syncing a carried copy | [Skill Ownership](skills/skill-ownership/SKILL.md) |

## Required Dependencies

Checks, audits, and sync use the Python 3 standard library only. Tools a workflow here
requires are setup work, not a reason to stop: reuse a working version, otherwise install at
user scope from the documented source and report what changed.

## Publication Security

Nothing reaches the remote before `bash scripts/check-disclosure.sh` passes locally.
[SECURITY.md](SECURITY.md) holds the gates; never relax a rule to publish a finding.

## Policy Synchronization

Keep this repository policy identical in `AGENTS.md` and `CLAUDE.md` when changing it.
