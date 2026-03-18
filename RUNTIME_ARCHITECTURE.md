# OpenBrain: Runtime Architecture

## Purpose

This document explains how the product is deployed and operated in the current phase.

It answers:
- what OpenBrain owns today
- what OpenClaw owns today
- which flows are event-driven versus scheduled

This is a runtime ownership and flow document. It complements:
- [README.md](README.md) for product and repo framing
- [USER_JOURNEYS.md](USER_JOURNEYS.md) for desired behavior
- [AGENT_OPERATING_MODEL.md](AGENT_OPERATING_MODEL.md) for shared agent posture
- [DESIGN_SPEC.md](DESIGN_SPEC.md) for implementation truth

## Current Phase

The current phase uses a two-system architecture:
- **OpenBrain** — the data layer
- **OpenClaw** — the orchestration layer

This split is intentional for speed, cost, and time-to-production. It is not necessarily the final product shape.

## Ownership Table

| Capability | Owner |
|---|---|
| Canonical stored state (Cosmos DB) | OpenBrain |
| MCP server and tool surface (7 tools) | OpenBrain |
| Vector search over documents | OpenBrain |
| Deterministic validation and mutation | OpenBrain |
| Recurring-task rollover logic | OpenBrain |
| Gateway and API surface | OpenClaw |
| Agent runtime and orchestration | OpenClaw |
| Scheduling and cron jobs | OpenClaw |
| Heartbeat | OpenClaw |
| Multi-channel delivery (Telegram, etc.) | OpenClaw |
| Daily briefing | OpenClaw |
| Nightly ping | OpenClaw |
| Conversational triage decisions | OpenClaw |
| Reminder scheduling | OpenClaw |
| Proactive outreach | OpenClaw |

## OpenBrain

OpenBrain is a pure data layer: an MCP server over Cosmos DB with vector search.

### MCP Tools

OpenBrain exposes 7 tools:

| Tool | Purpose |
|---|---|
| `write` | Create a new document |
| `read` | Retrieve a document by ID |
| `query` | Structured query over documents |
| `search` | Semantic vector search |
| `update` | Update an existing document |
| `delete` | Delete a document |
| `raw_query` | Execute a raw Cosmos DB query |

### OpenBrain does not own

- Reminder scheduling
- Proactive orchestration
- Background planning jobs
- Conversational triage decisions
- High-level prioritization decisions

## OpenClaw

OpenClaw is the orchestration layer. It owns interactive behavior, background execution, and proactive outreach.

### Responsibilities

- Gateway: receiving user brain dumps and questions
- Agent runtime: performing event-driven triage, reasoning, and dispatch
- Scheduling/cron: running periodic jobs (daily briefing, nightly ping, heartbeat)
- Multi-channel delivery: relaying responses, reminders, and suggestions to the user
- Deciding when to ask follow-up questions
- Calling OpenBrain tools for capture, retrieval, and updates

## Event-Driven Versus Scheduled Flows

### Event-driven flows

These happen in direct response to user interaction:
- Brain dump triage
- Write/update decisions
- Memory recall questions
- Task completion updates
- Follow-up questions for clarification

These are handled by OpenClaw, which calls OpenBrain tools as needed.

### Scheduled flows

These run on OpenClaw's cron schedule:
- Daily briefing
- Nightly ping
- Heartbeat
- Stale-goal and stale-idea resurfacing
- Broader review and planning passes

## Preferred Flow Story

1. The user interacts with OpenClaw.
2. OpenClaw uses OpenBrain for storage, retrieval, and deterministic updates.
3. OpenClaw handles reasoning, triage, and orchestration.
4. Any durable user state remains anchored in OpenBrain.
5. OpenClaw is the primary user-facing delivery layer for responses, reminders, and suggestions.

## Authority Boundaries

The same authority model from the behavior docs applies in this split runtime:
- Automatic for surfacing
- Confirmation for structuring
- Explicit approval for destructive or commitment-changing actions

That rule holds whether the action is triggered by OpenClaw inline or a scheduled job.

## Important Constraint

OpenBrain should remain the canonical product contract even while runtime behavior is split across systems.

That means:
- Behavior should be described in OpenBrain docs first
- Data written back into durable state should conform to OpenBrain schemas
- OpenClaw should be treated as an execution surface around the OpenBrain contract, not a separate product with competing truth
