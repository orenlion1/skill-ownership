# Skill Ownership

Good skills evolve. They are
[extracted from a hands-on task](https://agentskills.io/skill-creation/best-practices#extract-from-a-hands-on-task)
(the steps that worked, the corrections you made, the context the agent lacked) and then
[refined with real execution](https://agentskills.io/skill-creation/best-practices#refine-with-real-execution).
That loop never stops, and without an owner its output lands in the wrong place. A correction
made mid-task becomes one more "note for the agent" in AGENTS.md or CLAUDE.md, until the root
files are a manual. The release steps sit in the root file, again in a skill, and again in the
README; one copy changes, the others do not, and the agent follows whichever it read first.
Every line of a root file loads into every session, relevant or not. And unlike code, none of
it is reviewed against a contract or tested.

Skill ownership treats agent guidance as code: **one owner per rule**. Each skill owns its
workflow, guidance, and verification. The root files become a router: they say which request
goes to which skill and keep only the policy no skill covers. They open with this clause:

> This document routes requests to their owners. Each owner holds its workflow, guidance, and
> verification; follow the owner rather than restating or overriding it here. Everything else
> here is policy that no owner covers, and where such a policy limits an owner, the limit holds.

That gives each turn of the evolution loop a destination. A captured correction goes to the
skill that owns the work: the audit flags workflow text in a root file, and the refactor moves
it into its owner or into a new [coherent unit](https://agentskills.io/skill-creation/best-practices#design-coherent-units)
with its own route. A refinement is checked like a code change: every skill has an eval case,
a preservation check proves a rewrite kept every command, flag, path, and bound, and the size
ratchet makes each increase a recorded decision. An improved skill is shared by version, and
sync carries it to every repository that uses it without forking.

The result: a behavior changes in one place, the always-loaded text stays small, and agent
guidance gets the same review and CI as code. This repository is the upstream for the principle: the clause, the checks that
enforce it, and the skill that audits a repository and carries the contract by version. It
evolves the same way: its adoption steps began as commands in this README and now live in the
skill's Adopt section.

**You talk to the agent; the agent runs the tools.** Every step in
[Getting started](#getting-started) is a request you make to your coding agent, not a shell
command.

## Skill as code

Each skill is treated like a code module, and the checks hold it to that:

| In code | In a skill-owned repository |
| --- | --- |
| A module with one owner | A skill that owns one workflow: its steps, guidance, and verification |
| A public interface | The skill's description, which the router matches requests against |
| Unit tests | An eval case for every skill, run by the quality gate |
| A dispatch table | The root files: a routing table plus only the limits no skill covers |
| A linter in CI | The ownership checks, which fail when workflow text gathers in a root file or a route has no skill |
| A coverage ratchet | A size baseline: a skill grows only through a recorded, deliberate change |
| A dependency and its lockfile | The carried skill and its pin file, kept current by sync |

[The principle](skills/skill-ownership/references/principle.md) defines how each root-file
section is classified. This repository obeys its own checks: its root files are a routing
table, and CI fails when they drift.

### Best practices it codifies

Anthropic's [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
describe how to write one good skill. This repository turns several of them into checks that
fail, and applies the same discipline to the root files that route to your skills:

| Best practice | How it is enforced here |
| --- | --- |
| [Concise is key](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#concise-is-key) | Root files hold routes and limits only, under a line budget; workflow text moves into the skill that owns it |
| [Token budgets](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#token-budgets) | A per-skill size ratchet against a recorded baseline, so growth is always a reviewed decision |
| [Writing effective descriptions](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#writing-effective-descriptions) | Every description is one bounded line that states its trigger ("Use when", "Use for", or "Use only") |
| [Naming conventions](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#naming-conventions) | Skill names are lowercase and hyphenated, and match their directory |
| [Progressive disclosure patterns](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#progressive-disclosure-patterns) | Detail lives in references; a duplication check fails when a rule is stated in both a skill and its references, and every link and heading anchor must resolve |
| [Build evaluations first](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#build-evaluations-first) | Every skill needs an eval case; the quality gate runs them in CI, with optional execution against a model |
| [Provide utility scripts](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#provide-utility-scripts) and [Implement feedback loops](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#implement-feedback-loops) | One deterministic entry point runs every check and prints one line each, so the agent fixes and reruns until all pass |
| [Package dependencies](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#package-dependencies) | The checks use the Python standard library only: nothing to install |

Other items on the page's [checklist](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#checklist-for-effective-skills),
such as one-level-deep references, consistent terminology, avoiding time-sensitive
information, and testing with every model you use, are not checked here; review them by hand.

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
