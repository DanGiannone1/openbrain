# Claude Code Hooks

This repository enables two Claude hooks:

1. `UserPromptSubmit` -> `reinject-claude-md.py`
2. `PreToolUse` -> `safety-check.py`

## Purpose

- `reinject-claude-md.py`: Re-applies `CLAUDE.md` on every prompt to reduce instruction drift.
- `safety-check.py`: Blocks high-risk shell commands before they run.

## Setup

1. Keep the hook entries in `.claude/settings.local.json`.
2. Ensure Python is available as `python` in `PATH`.
3. Run `python .claude/hooks/test-safety-patterns.py` after modifying `safety-check.py`.
