# OpenBrain: Runtime Architecture

## Purpose

This document explains how the product is deployed and operated in the current phase.

It answers:
- what OpenBrain owns today
- what Command Center owns today
- what OpenClaw owns today
- which flows are event-driven versus scheduled
- how this interim architecture relates to the future holistic OpenBrain product

This is a runtime ownership and flow document. It complements:
- [README.md](C:/projects/openbrain/README.md) for product and repo framing
- [USER_JOURNEYS.md](C:/projects/openbrain/USER_JOURNEYS.md) for desired behavior
- [AGENT_OPERATING_MODEL.md](C:/projects/openbrain/AGENT_OPERATING_MODEL.md) for shared agent posture
- [DESIGN_SPEC.md](C:/projects/openbrain/DESIGN_SPEC.md) for implementation truth

## Current Phase

The current phase uses a pragmatic three-system architecture:
- OpenBrain
- Command Center
- OpenClaw

This split is intentional for speed, cost, and time-to-production.

It is not necessarily the final product shape.

## Future Direction

The future-state direction is for OpenBrain to become a more holistic product that owns more of the full "brain" experience inside this repo.

For now, however:
- OpenBrain is the canonical data and tool layer
- Command Center is the background execution layer
- OpenClaw is the interactive front door

That means the "brain" is a product-level concept spread across three runtime surfaces, even though the long-term intent is to unify more of it.

## System Responsibilities

### OpenBrain

OpenBrain owns:
- the canonical stored state
- the MCP server and tool surface
- deterministic validation and mutation behavior
- semantic recall over memories and ideas
- structured query over tasks, goals, misc, and settings
- recurring-task rollover logic

OpenBrain does not own:
- reminder scheduling
- proactive orchestration
- background planning jobs
- conversational triage decisions
- high-level prioritization decisions

### Command Center

Command Center owns background execution in the current phase.

Typical responsibilities:
- scheduled deep-dive analysis across stored state
- background synthesis such as planning or status proposals
- heavier asynchronous jobs that should not block the live conversation flow
- dispatch and execution management for agent jobs

Command Center should not become the source of truth for user state. It should read from OpenBrain and, when appropriate, write durable outputs back through explicit OpenBrain-compatible contracts.

Preferred agent posture for Command Center jobs:
- use narrowly scoped OpenBrain MCP tools by default
- avoid Bash and general repo exploration unless there is a specific infrastructure/debugging task
- treat background agents as state-aware utilities, not broad coding agents

### OpenClaw

OpenClaw owns interactive behavior in the current phase.

Typical responsibilities:
- receiving user brain dumps and questions
- performing event-driven triage inline where possible
- calling OpenBrain tools directly for capture, retrieval, and updates
- deciding when to ask follow-up questions
- relaying reminders, summaries, or planning suggestions back to the user
- optionally dispatching heavier jobs to Command Center when immediate inline handling is not the right fit

## Event-Driven Versus Scheduled Flows

### Event-driven flows

These should happen in direct response to user interaction:
- brain dump triage
- write/update decisions
- memory recall questions
- task completion updates
- small follow-up questions for clarification

Default posture:
- handle inline in OpenClaw when possible
- dispatch to Command Center only when the work is heavy, multi-step, or intentionally asynchronous

Likely current fit:
- brain dump triage should stay primarily event-driven
- OpenClaw may perform triage inline or immediately dispatch a constrained triage agent job

### Scheduled flows

These are better suited to Command Center in the current phase:
- broad daily review across all stored state
- planning summaries
- stale-goal and stale-idea resurfacing
- larger pattern-analysis passes

The system may later persist more of these outputs directly in OpenBrain once the appropriate document contracts are defined.

## Preferred Flow Story

The intended story across the three systems is:

1. The user interacts with OpenClaw.
2. OpenClaw uses OpenBrain for storage, retrieval, and deterministic updates.
3. OpenClaw handles lightweight reasoning inline.
4. Command Center handles scheduled or heavier background cognition.
5. Any durable user state remains anchored in OpenBrain.
6. OpenClaw remains the primary user-facing delivery layer for responses, reminders, and suggestions.

## Authority Boundaries

The same authority model from the behavior docs still applies in this split runtime:
- automatic for surfacing
- confirmation for structuring
- explicit approval for destructive or commitment-changing actions

That rule should hold whether the action is triggered by:
- OpenClaw inline
- a Command Center background job
- a later unified OpenBrain-native workflow

## Important Constraint

OpenBrain should remain the canonical product contract even while runtime behavior is split across systems.

That means:
- behavior should be described in OpenBrain docs first
- data written back into durable state should conform to OpenBrain schemas
- Command Center and OpenClaw should be treated as execution surfaces around the OpenBrain contract, not separate products with competing truth

## Open Questions

- which background outputs should eventually be stored durably in OpenBrain
- whether brain dump triage should remain primarily inline in OpenClaw or move behind immediate job dispatch
- when the current three-system architecture should collapse into a more unified OpenBrain runtime
