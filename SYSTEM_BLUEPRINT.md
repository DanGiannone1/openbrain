# Open Brain: System Blueprint

## Purpose

This document explains the product context and conceptual model behind OpenBrain.

It is not the implementation contract. For runtime behavior, schema details, and server-side rules, use [DESIGN_SPEC.md](C:/projects/openbrain/DESIGN_SPEC.md).

OpenBrain is a low-friction, AI-native "second brain" for capturing and retrieving personal knowledge, ideas, goals, and tasks without forcing heavy manual organization.

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

## Product Experience

The desired product experience is:

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

### Semantic Recall

The semantic layer is optimized for natural-language retrieval:
- `memory`: factual or reference information you want to recall later
- `idea`: speculative or generative thoughts worth revisiting later

### Deterministic State

The operational layer is for trackable user state:
- `goal`: long-running objectives
- `task`: concrete work items, either one-time or recurring
- `misc`: ambiguous captures preserved without forced classification
- `userSettings`: per-user configuration such as tag taxonomy

Recurring tasks use two separate concepts:
- `recurrenceDays`: cadence
- `dueDate`: next upcoming occurrence

Marking a recurring task complete should move the next `dueDate` forward. The server stores and mutates that state; it does not decide what should be worked on.

Reminders are not a stored document type. They are external behavior layered on top of goals and tasks.

## Runtime Shape

- MCP server hosted in Azure Container Apps
- Azure Cosmos DB for NoSQL with vector search
- Foundry / Azure OpenAI-backed embeddings
- External agents and clients interacting through MCP tools

## Golden Rules

- The server stores, embeds, queries, and updates documents. It does not decide what matters.
- Agents or clients own classification, prioritization, cleanup, and reminder logic.
- The schema should stay flexible enough to preserve weird or incomplete input without breaking.
- The system should reduce friction, not add workflow burden.

## Future Direction

Future workflows may include richer ingestion, better reminder behavior, or tighter planning loops, but those should sit on top of the stored data rather than inside the core MCP server contract.
