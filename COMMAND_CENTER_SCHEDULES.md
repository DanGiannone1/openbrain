# Command Center Schedules

This repo includes background-agent markdown intended for command-center style dispatch and scheduled execution.

## Recommended Agents

- [triage.md](C:/projects/openbrain/.claude/agents/triage.md)
- [cleanup.md](C:/projects/openbrain/.claude/agents/cleanup.md)
- [taxonomy-maintainer.md](C:/projects/openbrain/.claude/agents/taxonomy-maintainer.md)
- [goal-maintainer.md](C:/projects/openbrain/.claude/agents/goal-maintainer.md)

## Suggested Schedule Cadence

- `triage`
  - trigger: event-driven from incoming Telegram or other intake pipeline
  - purpose: convert raw dumps into first-pass documents

- `cleanup`
  - cadence: every 6 hours
  - purpose: dedupe memories, reclassify `misc`, clean stale tags

- `taxonomy-maintainer`
  - cadence: daily
  - purpose: keep the user-managed tag taxonomy coherent

- `goal-maintainer`
  - cadence: daily
  - purpose: detect stale goals and create or suggest next-step tasks

## Dispatch Inputs

Recommended command-center dispatch values for this repo:

- `repo_url`: `https://github.com/DanGiannone1/openbrain.git`
- `local_path`: `openbrain`

## Notes

- The server remains a data layer. Background agents own reasoning, cleanup, and prioritization.
- `misc` is query-only until reclassified.
- Tag taxonomy is stored in the `userSettings` document in Cosmos.
