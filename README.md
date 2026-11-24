# Skill Ownership

One owner per rule. A repository's root files (AGENTS.md, CLAUDE.md) open with the ownership
clause and act as a router: they say which request goes to which skill and keep only the
policy no skill covers. Each skill owns its workflow, guidance, and verification.

> This document routes requests to their owners. Each owner holds its workflow, guidance, and
> verification; follow the owner rather than restating or overriding it here. Everything else
> here is policy that no owner covers, and where such a policy limits an owner, the limit holds.

This repository is the upstream for that principle: the clause, the checks that enforce it,
and the skill that audits a repository and carries the contract by version.

## Getting started

This guide takes a repository from nothing to a passing check. Each step names what to ask
your coding agent; the [skill](skills/skill-ownership/SKILL.md) holds the exact commands,
examples, and when to use each one.

You need a coding agent that reads AGENTS.md or CLAUDE.md, such as Claude Code or Codex; it
handles Python and git for you.

### 1. Import the skill

Ask the agent: *"Adopt skill ownership from <https://github.com/orenlion1/skill-ownership> in
this repository."*

The link tells the agent where the skill lives, since your repository does not carry it yet.
The agent clones this repository next to yours and runs the first adoption from it. That
copies the latest release into your skills/skill-ownership/ directory and writes
policy/skill-ownership-pin.json, which records the release and commit you carry. Nothing is
committed: review the new files and deliver them through your normal review path.
Start from a clean working tree so the review shows only the import.

To run the import yourself, follow [Adopt](skills/skill-ownership/SKILL.md#adopt).

### 2. Route requests to the skill

Give the skill a row in the routing table of both root files, so the agent knows to use it.
If the repository has no root files yet, create AGENTS.md and CLAUDE.md with one title, the
clause above, and the routing table. Keep the two files identical.

### 3. Audit

Ask the agent: *"Audit this repository against skill ownership."*

The audit is read-only. It sorts every root-file section into a route, residual policy, or
workflow that belongs in a skill, and lists unrouted skills, routes without a skill, oversized
skills, and broken links. Its classes are proposals; read each section before acting on one.
See [Audit](skills/skill-ownership/SKILL.md#audit).

### 4. Refactor

Ask the agent: *"Refactor the root files into a routing table."*

The agent moves each workflow section into the skill that owns it, leaves a route behind,
adds the policy files the checks read, and proves no command, flag, or path was lost in the
move. See [Refactor](skills/skill-ownership/SKILL.md#refactor).

### 5. Run the checks

Ask the agent: *"Run the skill ownership checks."*

Every check prints one line. Before the refactor, failures for the root contract are
expected; afterwards everything you rely on should pass and nothing should report "not
configured". Add the checks to continuous integration so they run on every pull request.
See [Checks](skills/skill-ownership/SKILL.md#checks).

### 6. Stay current

Ask the agent: *"Is our skill-ownership copy up to date?"* and, when it is behind, *"Update
skill ownership to the latest release."*

The report is read-only and tells you whether you are current, behind, or carry undeclared
changes. The update replaces the carried copy and the pin together and never commits. Files
you changed on purpose are declared in the pin and kept. See
[Sync](skills/skill-ownership/SKILL.md#sync).

## Layout

| Path | Purpose |
| --- | --- |
| [skills/skill-ownership/](skills/skill-ownership/) | The skill and everything a downstream repository carries |
| [scripts/](scripts/) | Repository-only entry points: checks, release metadata, disclosure scans |
| [skill_evals/](skill_evals/) | Eval cases, one per skill |
| [policy/](policy/) | This repository's own policy files; it obeys its own checks |
| [tests/](tests/) | Fixture tests |
| [security/](security/) | Disclosure policy for the publication gates |

## Contributing

[CLAUDE.md](CLAUDE.md) routes work in this repository. The repository check covers release
metadata, tests, and root-file identity, and the disclosure scan must pass locally before
anything is pushed; [SECURITY.md](SECURITY.md) holds its gates.

## Releases

Ask the coding agent to *"run release-it"*. [VERSIONING.md](VERSIONING.md) is the release
contract: one version file, a protected pull request, one annotated tag, exact-SHA CI, and a
curated GitHub Release.

## License

[MIT](LICENSE).
