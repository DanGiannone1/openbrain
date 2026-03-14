---
name: data-models
description: Review and modify the OpenBrain data model, document schemas, and task/goal/memory/idea business rules. Use when changing document fields, recurring task behavior, tag taxonomy handling, searchability rules, or any contract in DESIGN_SPEC.md, src/openbrain/models/, or src/openbrain/services/document_service.py.
---

# OpenBrain Data Models

Use this skill when changing OpenBrain schemas or business rules.

## Source Of Truth Order

Check these in order before editing anything:

1. [DESIGN_SPEC.md](C:/projects/openbrain/DESIGN_SPEC.md)
2. [src/openbrain/models](C:/projects/openbrain/src/openbrain/models)
3. [src/openbrain/services/document_service.py](C:/projects/openbrain/src/openbrain/services/document_service.py)
4. [tests/test_document_service.py](C:/projects/openbrain/tests/test_document_service.py)
5. [tests/test_scenarios.py](C:/projects/openbrain/tests/test_scenarios.py)

Treat the spec as the behavioral source of truth unless the user explicitly decides to change it.

## Boundaries

- Keep OpenBrain as a data layer.
- Do not add agent orchestration, scheduling, or auto-generated user content to this repo unless the user explicitly asks for it.
- Put schema definitions in `src/openbrain/models/`.
- Put server-side mutation logic in `src/openbrain/services/document_service.py`.
- Put persistence/query mechanics in `src/openbrain/cosmos_client.py`.
- Put examples, seed content, and migration input in dedicated docs or scripts, never inline in the service layer.

## Recurring Task Rule

For recurring tasks:

- `recurrenceDays` defines cadence.
- `dueDate` defines the next occurrence.
- Marking a recurring task `done` must roll `dueDate` forward by `recurrenceDays` and reopen the task.
- For "what is coming up?" behavior, recurring tasks should have an explicit initial `dueDate`.
- If the user does not provide an initial `dueDate`, prefer seeding `dueDate = createdAt + recurrenceDays` rather than leaving it null.

If you change this rule:

1. Update [DESIGN_SPEC.md](C:/projects/openbrain/DESIGN_SPEC.md).
2. Update runtime logic in [document_service.py](C:/projects/openbrain/src/openbrain/services/document_service.py).
3. Update or add tests in [test_document_service.py](C:/projects/openbrain/tests/test_document_service.py) and [test_scenarios.py](C:/projects/openbrain/tests/test_scenarios.py).

## Change Checklist

When modifying data model behavior:

1. Confirm the exact intended behavior in the spec.
2. Update the model definitions if the shape changes.
3. Update the service-layer logic if mutation or defaults change.
4. Update migration/seed docs if they depend on the old behavior.
5. Run the relevant tests, then the full suite if the change is broad.
6. Commit the change immediately after validation.

## Common File Targets

- Schema fields: [src/openbrain/models](C:/projects/openbrain/src/openbrain/models)
- Write/update behavior: [src/openbrain/services/document_service.py](C:/projects/openbrain/src/openbrain/services/document_service.py)
- Search/query behavior: [src/openbrain/cosmos_client.py](C:/projects/openbrain/src/openbrain/cosmos_client.py)
- Seed data: [openbrain-migration-items.md](C:/projects/openbrain/openbrain-migration-items.md)
- Hosted seeding script: [scripts/seed_openbrain_items.py](C:/projects/openbrain/scripts/seed_openbrain_items.py)

