# openbrain

OpenBrain is an MCP server plus Azure deployment surface for storing and retrieving personal knowledge, ideas, goals, and tasks.

Start here:
- product and repo contract: [DESIGN_SPEC.md](DESIGN_SPEC.md)
- high-level product context: [SYSTEM_BLUEPRINT.md](SYSTEM_BLUEPRINT.md)
- local MCP/tooling setup: [MCP_INTEGRATIONS.md](MCP_INTEGRATIONS.md)
- curated seed/import data: [openbrain-migration-items.md](openbrain-migration-items.md)

## Documentation Map

| Document | Role |
|---|---|
| [DESIGN_SPEC.md](DESIGN_SPEC.md) | Source of truth for architecture, schemas, and behavioral rules |
| [SYSTEM_BLUEPRINT.md](SYSTEM_BLUEPRINT.md) | High-level product context and conceptual model |
| [MCP_INTEGRATIONS.md](MCP_INTEGRATIONS.md) | Repo MCP configuration and local tooling setup |
| [openbrain-migration-items.md](openbrain-migration-items.md) | Curated seed/import data only |
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

1. `DESIGN_SPEC.md`
2. runtime code in `src/openbrain/`
3. tests
4. `SYSTEM_BLUEPRINT.md`
5. migration/seed docs

`SYSTEM_BLUEPRINT.md` provides intent and product context. It should not override the implementation contract in `DESIGN_SPEC.md`.

This repo now includes a checked-in `.mcp.json` for:

- Open Brain local MCP server
- Azure MCP Server
- Microsoft Learn MCP Server
