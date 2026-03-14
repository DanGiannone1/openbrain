# openbrain

OpenBrain is an MCP server plus Azure deployment surface for storing and retrieving personal knowledge, ideas, goals, and tasks.

It is a low-friction, AI-native second brain for capturing and retrieving personal knowledge, ideas, goals, and tasks without forcing heavy manual organization.

## Repo Boundary

This repository owns:
- the MCP server
- the Azure deployment surface
- the document model and server-side mutation rules

This repository does not own:
- Telegram or any other ingestion client
- external schedulers or orchestrators
- reminder delivery
- agent-side classification, prioritization, or cleanup decisions
- a human-facing UI

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

## Product Experience

The intended product experience is:

1. Low-friction capture
   Users should be able to brain dump facts, ideas, goals, and tasks without navigating a rigid UI.
2. Reliable recall
   Users should be able to ask natural-language questions later and retrieve the right stored information.
3. Structured state where needed
   Goals and tasks should support lightweight tracking without turning the MCP server into a full planning engine.
4. Agent-assisted organization
   External agents may help classify, update, prioritize, or remind, but those behaviors sit on top of the MCP server rather than inside it.

## Conceptual Model

OpenBrain separates semantic recall from operational state.

Semantic recall:
- `memory`: factual or reference information you want to recall later
- `idea`: speculative or generative thoughts worth revisiting later

Deterministic state:
- `goal`: long-running objectives
- `task`: concrete work items, either one-time or recurring
- `misc`: ambiguous captures preserved without forced classification
- `userSettings`: per-user configuration such as tag taxonomy and behavior preferences

Recurring tasks use two separate concepts:
- `recurrenceDays`: cadence
- `dueDate`: next upcoming occurrence

Marking a recurring task complete should move the next `dueDate` forward. The server stores and mutates that state; it does not decide what should be worked on.

Reminders are not a stored document type. They are external behavior layered on top of goals and tasks.

## Golden Rules

- The server stores, embeds, queries, and updates documents. It does not decide what matters.
- Agents or clients own classification, prioritization, cleanup, and reminder logic.
- The schema should stay flexible enough to preserve weird or incomplete input without breaking.
- The system should reduce friction, not add workflow burden.

Behavior is intentionally documented at two levels:
- [USER_JOURNEYS.md](USER_JOURNEYS.md) describes what the system should do for the user
- [AGENT_BEHAVIOR_PROMPT.md](AGENT_BEHAVIOR_PROMPT.md) describes how an agent layered on top of OpenBrain should behave

Those documents define capability and posture, not hard operational cadences. Exact timing for reminders, check-ins, and resurfacing should be shaped by user preference and iteration rather than treated as fixed product truth.

Start here:
- expected behavior and requirements: [USER_JOURNEYS.md](USER_JOURNEYS.md)
- product and repo contract: [DESIGN_SPEC.md](DESIGN_SPEC.md)
- local MCP/tooling setup: [MCP_INTEGRATIONS.md](MCP_INTEGRATIONS.md)

## Documentation Map

| Document | Role |
|---|---|
| [USER_JOURNEYS.md](USER_JOURNEYS.md) | User-facing and agent-facing expected behavior |
| [DESIGN_SPEC.md](DESIGN_SPEC.md) | Source of truth for architecture, schemas, and behavioral rules |
| [AGENT_BEHAVIOR_PROMPT.md](AGENT_BEHAVIOR_PROMPT.md) | Reusable agent prompt and reasoning-vs-determinism guide |
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
2. `AGENT_BEHAVIOR_PROMPT.md`
3. `DESIGN_SPEC.md`
4. runtime code in `src/openbrain/`
5. tests

`README.md` gives the high-level product and repo framing. `USER_JOURNEYS.md` captures desired product behavior. `AGENT_BEHAVIOR_PROMPT.md` captures the intended agent operating posture. `DESIGN_SPEC.md` captures the implementation contract.

This repo now includes a checked-in `.mcp.json` for:

- Open Brain local MCP server
- Azure MCP Server
- Microsoft Learn MCP Server
