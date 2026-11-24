# Skill Ownership

Skill usefulness evolves: skills are
[extracted from a hands-on task](https://agentskills.io/skill-creation/best-practices#extract-from-a-hands-on-task)
and [refined with real execution](https://agentskills.io/skill-creation/best-practices#refine-with-real-execution).
Each refinement corrects one capability: a BigQuery analysis learns to
[always exclude test accounts](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#develop-skills-iteratively-with-claude); a Word edit
learns to [validate the XML after every change](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#implement-feedback-loops). With no specific
skill responsible for the capability, the correction becomes one more note in AGENTS.md or
CLAUDE.md, loaded into every session, even one that only edits a Word document. Notes pile
up, copies of the same rule drift, and none of it is tested.

A repository of agent skills serves one **domain**: a set of skills for one area of work, with
AGENTS.md and CLAUDE.md as the router.

- Production investigations: skills for querying Grafana, AWS, and Slack, citing evidence,
  and writing reports.
- Incident reviews: skills for post-incident reviews and their recurring placeholders.
- Development delivery: skills for running development tasks through to delivery.

Skill ownership splits that domain into modular units: **skills, each owning one
capability**. A skill holds its capability's workflow, guidance, and verification, the way a
module owns one responsibility in code, so the test-account filter belongs to the
data-analysis skill and the validation loop to the document-editing skill. The root files are
not a skill: they are the domain's router, sending each request to the skill that owns it and
keeping only the policy no skill covers. They open with this clause:

> This document routes requests to their owners. Each owner holds its workflow, guidance, and
> verification; follow the owner rather than restating or overriding it here. Everything else
> here is policy that no owner covers, and where such a policy limits an owner, the limit holds.

Every correction then lands in the skill responsible for that capability, every rewrite is
checked like a code change, and an improved skill reaches other repositories by version
instead of by copy. This repository is the upstream: the clause, the checks that enforce it,
and the skill that adopts, audits, and syncs it. It obeys its own checks.

## Skill as code

| In code | Here | Best practice it enforces |
| --- | --- | --- |
| A module with one responsibility | A skill owns one capability; workflow text found in a root file moves to that skill | [Design coherent units](https://agentskills.io/skill-creation/best-practices#design-coherent-units) |
| A dispatch table | Root files hold routes and limits only, under a line budget | [Concise is key](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#concise-is-key) |
| A public interface | A kebab-case name matching its directory, and a one-line description that states its trigger | [Writing effective descriptions](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#writing-effective-descriptions), [Naming conventions](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#naming-conventions) |
| Unit tests | An eval case for every skill, run in CI | [Build evaluations first](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#build-evaluations-first) |
| A coverage ratchet | A skill grows only through a recorded size baseline; a rewrite must keep every command, flag, path, and bound | [Token budgets](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#token-budgets) |
| Single source of truth | Detail lives in references; a rule stated in both a skill and its references fails, and every link must resolve | [Progressive disclosure patterns](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#progressive-disclosure-patterns) |
| A linter | One standard-library entry point runs every check, one line each, so the agent fixes and reruns | [Implement feedback loops](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#implement-feedback-loops) |
| A dependency and its lockfile | The carried skill and its pin file, kept current by sync | — |

The rest of the [checklist](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#checklist-for-effective-skills),
such as consistent terminology and testing with every model you use, needs review by hand.
[The principle](skills/skill-ownership/references/principle.md) defines how root-file
sections are classified.

## Getting started

You need a coding agent that reads AGENTS.md or CLAUDE.md, such as Claude Code or Codex. The
[skill](skills/skill-ownership/SKILL.md) holds the commands behind each step.

**You talk to the agent; the agent runs the tools.**

Copy each request into the agent, in order.

### 1. Import

```text
Adopt skill ownership from https://github.com/orenlion1/skill-ownership in this repository.
```

The agent copies the latest release into skills/skill-ownership/ and records it in
policy/skill-ownership-pin.json, without committing. Start from a clean working tree. See
[Adopt](skills/skill-ownership/SKILL.md#adopt).

### 2. Route

```text
Route skill ownership in AGENTS.md and CLAUDE.md, and keep the two files identical.
```

The skill gets a row in the routing table of both root files. A repository without root files
gets them with a title, the clause, and the table.

### 3. Audit

```text
Audit this repository against skill ownership.
```

A read-only report that classifies every root-file section; treat its classes as proposals.
See [Audit](skills/skill-ownership/SKILL.md#audit).

### 4. Refactor

```text
Refactor the root files into a routing table.
```

Workflow text moves to its owning skill and leaves a route behind. See
[Refactor](skills/skill-ownership/SKILL.md#refactor).

### 5. Check

```text
Run the skill ownership checks, then add them to CI.
```

Every check prints one line; all should pass after the refactor. See
[Checks](skills/skill-ownership/SKILL.md#checks).

### 6. Stay current

```text
Is our skill-ownership copy up to date? If it is behind, update it to the latest release.
```

The report is read-only; the update replaces the carried copy and the pin together, without
committing. See [Sync](skills/skill-ownership/SKILL.md#sync).

## Layout

| Path | Purpose |
| --- | --- |
| [skills/skill-ownership/](skills/skill-ownership/) | The skill and everything a downstream repository carries |
| [scripts/](scripts/) | Repository-only checks, release metadata, and disclosure scans |
| [skill_evals/](skill_evals/) | Eval cases, one per skill |
| [policy/](policy/) | This repository's own policy files |
| [tests/](tests/) | Fixture tests |
| [security/](security/) | Disclosure policy for the publication gates |

## Contributing and releases

[CLAUDE.md](CLAUDE.md) routes work here, and [SECURITY.md](SECURITY.md) holds the disclosure
gates that must pass before any push. To release, ask the agent to *"run release-it"*;
[VERSIONING.md](VERSIONING.md) is the release contract.

## License

[MIT](LICENSE).
