# openbrain

Project MCP integrations are documented in [MCP_INTEGRATIONS.md](MCP_INTEGRATIONS.md).

## Documentation Map

- [DESIGN_SPEC.md](DESIGN_SPEC.md): architecture, schemas, and behavioral rules
- [openbrain-migration-items.md](openbrain-migration-items.md): curated seed/import data
- [src/openbrain/models](src/openbrain/models): Pydantic document shapes
- [src/openbrain/services/document_service.py](src/openbrain/services/document_service.py): server-side document mutation and recurring-task behavior
- [tests/test_document_service.py](tests/test_document_service.py): focused business-logic tests
- [tests/test_scenarios.py](tests/test_scenarios.py): scenario coverage across document flows

## Where Business Logic Lives

Use this rule of thumb:

- schema and behavior definition: `DESIGN_SPEC.md`
- server-side business logic: `src/openbrain/services/document_service.py`
- persistence/query mechanics: `src/openbrain/cosmos_client.py`
- verification of expected behavior: tests

Example: recurring task rules belong in the spec first, then in `document_service.py`, then in tests. They should not live only in prompts, migration notes, or agent scaffolding.

This repo now includes a checked-in `.mcp.json` for:

- Open Brain local MCP server
- Azure MCP Server
- Microsoft Learn MCP Server
