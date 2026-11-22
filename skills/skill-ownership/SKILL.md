---
name: skill-ownership
description: "Audit a repository against the skill ownership principle and refactor it toward a routing table with one owner per rule. Use when adopting, checking, or syncing the ownership contract."
metadata:
  version: "0.1.0"
---

# Skill Ownership

## Overview

The ownership clause opens a repository's root files:

> This document routes requests to their owners. Each owner holds its workflow, guidance, and
> verification; follow the owner rather than restating or overriding it here. Everything else
> here is policy that no owner covers, and where such a policy limits an owner, the limit holds.

A root file is a router. Each rule has exactly one owner, a skill, and the root file keeps
only the routing table and the residual policy no skill covers.

## When to Use

- Adopting the principle in a repository, or checking that a repository still obeys it.
- Syncing a carried copy of this skill to a newer release.

## Checks

Run every check from the repository root. A check whose optional policy is absent reports
`not configured`; a malformed policy fails closed.

```sh
python3 skills/skill-ownership/scripts/ownership.py check --repository .
```

## Common Rationalizations

| Rationalization | Reality |
| --- | --- |
| "Allowlist the section so the check passes." | A section that holds steps is workflow; it moves to its owning skill and the root file keeps a route. |
| "Record a bigger baseline; the skill needed the text." | Detail a reader rarely needs belongs in a reference; record growth only when the always-loaded text earns it. |

## Red Flags

- A root-file section that tells the reader how to do something rather than who owns it.
- A skill with no routing row, or a routing row with no skill.
- A policy minimum lowered to make a run pass.

## Verification

- `ownership.py check` passes with no check silently unconfigured that the repository relies on.
- The root files are byte-identical and open with the clause.
