# openbrain

OpenBrain is an MCP server plus Azure deployment surface for storing and retrieving personal knowledge, ideas, goals, and tasks.

## What OpenBrain Does

At the highest level, OpenBrain exists to do six things for the user:

1. Capture
   Get facts, ideas, goals, and tasks out of the user's head with very little friction.
2. Organize
   Keep stored information coherent over time through classification, cleanup, and lightweight structure.
3. Recall
   Answer natural-language questions about what the user has previously captured.
4. Track
   Maintain operational state for one-time tasks, recurring tasks, and goals.
5. Coach
   Help the user make progress on important goals without turning the system into a rigid productivity app.
6. Prompt
   Provide useful proactive outreach such as reminders, stale-goal nudges, and planning support.

The intended product stance is:
- more active than a passive archive
- less intrusive than a nagging task manager
- useful as an organized assistant
- eventually capable of acting like a lightweight chief of staff

For the fuller behavior-oriented view, use [USER_JOURNEYS.md](USER_JOURNEYS.md).

Start here:
- expected behavior and requirements: [USER_JOURNEYS.md](USER_JOURNEYS.md)
- product and repo contract: [DESIGN_SPEC.md](DESIGN_SPEC.md)
- high-level product context: [SYSTEM_BLUEPRINT.md](SYSTEM_BLUEPRINT.md)
- local MCP/tooling setup: [MCP_INTEGRATIONS.md](MCP_INTEGRATIONS.md)

## Documentation Map

| Document | Role |
|---|---|
| [USER_JOURNEYS.md](USER_JOURNEYS.md) | User-facing and agent-facing expected behavior |
| [DESIGN_SPEC.md](DESIGN_SPEC.md) | Source of truth for architecture, schemas, and behavioral rules |
| [SYSTEM_BLUEPRINT.md](SYSTEM_BLUEPRINT.md) | High-level product context and conceptual model |
| [MCP_INTEGRATIONS.md](MCP_INTEGRATIONS.md) | Repo MCP configuration and local tooling setup |
| [CLAUDE.md](CLAUDE.md) | Claude repo operating rules |
| [AGENTS.md](AGENTS.md) | Codex repo operating rules |
| [.claude/hooks/README.md](.claude/hooks/README.md) | Claude hook wiring and purpose |

Code locations:
- [src/openbrain/models](src/openbrain/models): Pydantic document shapes
- [src/openbrain/services/document_service.py](src/openbrain/services/document_service.py): server-side document mutation and recurring-task behavior
- [src/openbrain/cosmos_client.py](src/openbrain/cosmos_client.py): Cosmos persistence and vector query behavior
- [tests/test_document_service.py](tests/test_document_service.py): focused business-logic tests
- [tests/test_scenarios.py](tests/test_scenarios.py): scenario coverage across document flows

## Where Business Logic Lives

Use this rule of thumb:

- schema and behavior definition: `DESIGN_SPEC.md`
- server-side business logic: `src/openbrain/services/document_service.py`
- persistence/query mechanics: `src/openbrain/cosmos_client.py`
- verification of expected behavior: tests

Example: recurring task rules belong in the spec first, then in `document_service.py`, then in tests. They should not live only in prompts, migration notes, or agent scaffolding.

## Source Of Truth Order

When there is tension between docs, use this order:

1. `USER_JOURNEYS.md`
2. `DESIGN_SPEC.md`
3. runtime code in `src/openbrain/`
4. tests
5. `SYSTEM_BLUEPRINT.md`

`USER_JOURNEYS.md` captures desired behavior. `DESIGN_SPEC.md` captures the implementation contract. `SYSTEM_BLUEPRINT.md` provides broader context and should not override either one.

This repo now includes a checked-in `.mcp.json` for:

- Open Brain local MCP server
- Azure MCP Server
- Microsoft Learn MCP Server
