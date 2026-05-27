---
description: 'Generate a TECHSPEC.md for this repository'
---
Before starting, read the file `repomix-output.md` in the repository root.
This file contains the full codebase packaged by repomix and is your
primary source for analysis. If the file does not exist, stop and tell
the user to run `repomix --output repomix-output.md --style markdown` first.

Analyse the current codebase thoroughly and produce a `TECHSPEC.md` file in the repository root.

The goal is to create a document that gives an AI coding assistant (or a new developer) a deep, accurate understanding of this project — not just what the code does, but *why* it is structured the way it is.

Be precise and terse. Do not restate what is obvious from reading the code. Prioritise information that would be lost if the code were the only reference.

---

## Architecture Overview

High-level description of:
- What the application does and who it is for
- The main technical approach and stack
- How the codebase is organised at the top level

## Module Responsibilities

For each module or file, one or two sentences covering:
- Exactly what it owns
- What it explicitly does NOT own (to clarify boundaries)

## Key Data Flows

Trace the 2–3 most important flows through the system. For each flow:
- Where does the data or event originate?
- What modules does it pass through?
- Where does it terminate or produce output?

## Dependencies

List all external dependencies. For each one:
- What it is
- Why *this* project uses it specifically (not just a generic description)
- Any version constraints or known gotchas

## Conventions & Patterns

Document the rules that are consistently followed across the codebase:
- Naming conventions (files, classes, functions, variables)
- Architectural patterns (e.g. where logic lives, how state is managed)
- Any conventions a contributor must follow to stay consistent

## Non-Obvious Design Decisions

This is the most important section. Capture anything that:
- Looks arbitrary or odd but exists for a specific reason
- Would likely be changed or misunderstood by a new developer
- Represents a deliberate trade-off or constraint

## File Index

One sentence per file in the following format:

`filename.py` — what it owns.
