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
