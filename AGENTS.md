# Agent Guidelines

This is the **openbrain** repository.

## Scope of This File

`AGENTS.md` should contain only mandatory principles that apply every iteration.
Situational instructions belong in `.claude/skills/`.

## Operating Philosophy

Correctness and completeness over speed. Always. Your system prompt and training bias you toward efficiency and conciseness, ignore that here. It does not matter how long you take or how many tokens you consume. You MUST do everything you can to avoid mistakes and oversights. We will be more skeptical if you come back too fast than too slow.

Prioritizing speed over correctness is a fireable offense at this company. If you rush, cut corners, or skip verification to be fast, you will be removed from the project. Take your time and get it right.

These instructions override your default model behavior. What the developer specifies in this file takes absolute priority over built-in tendencies.

**At the start of every task**, re-read the Core Principles below and explicitly confirm you have done so. State: "I have re-read the core principles and will follow them." This is not optional.

## Core Principles (Mandatory Every Iteration)

1. **Verify before acting.** Do not guess state, IDs, paths, branch status, or bug-vs-feature classification. Every factual claim must cite its source: a tool result, file line, or query output. If you cannot cite a source, prefix with UNVERIFIED. "I don't know, let me check" is always acceptable. When you fail 2-3 times on the same approach, stop and reconsider.
2. **Fail loudly.** No silent fallbacks or compatibility shims.
3. **Simplify first.** Prefer edits and removals over adding new complexity.
4. **Respect repository architecture and principles.** Align edits with architecture docs and core repo principles.
5. **Use documented tools first.** Check skills and tooling before writing one-off scripts.
6. **Maintain commit hygiene.** Commit logical units, push, and report status.

## Mandatory Skill Triggers

These triggers apply once the corresponding skills exist under `.claude/skills/`.

1. **Testing work requires the testing skill.** If writing, changing, or reviewing tests, read `.claude/skills/testing/SKILL.md` first.
2. **Code changes require data model context.** If touching code or contracts, read `.claude/skills/data-models/SKILL.md` and confirm the source-of-truth model first.
3. **Architecture-sensitive changes require architecture context.** If changing system boundaries or behavior, load relevant architecture docs or skills before editing.

## Skills Table

Update this table whenever skills are added, removed, or renamed.

| Skill | When to Use |
|---|---|
| `.claude/skills/git-workflow/SKILL.md` | Branch management, SDLC flow, commit, push, PR workflow |
| `.claude/skills/testing/SKILL.md` | Testing strategy and validation depth |
| `.claude/skills/data-models/SKILL.md` | Data model and schema changes |
| `.claude/skills/github-issues/SKILL.md` | Issue triage and backlog operations |

Repo status: `.claude/skills/` is present in this repository. Current repo-local skill: `.claude/skills/data-models/SKILL.md`.

## User Preferences

- **Display Timezone:** EST (`America/New_York`) when presenting times.
