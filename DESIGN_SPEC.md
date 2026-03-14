# Open Brain: Technical Design Specification

> Version: 3.4
> Date: 2026-03-12
> Status: Baseline for implementation
> Repository: `openbrain`

## 1. Purpose

Open Brain is an MCP server that stores personal life-state documents, generates embeddings, and serves retrieval, query, and update operations to external agents and clients.

This repo owns the MCP server and its deployment surface.

This repo does not own:
- Telegram ingestion
- Triage, deduplication, prioritization, or cleanup reasoning
- Human-facing UI
- External schedulers and orchestrators

## 2. Core Principles

| Principle | Implication |
|---|---|
| Server = data layer | The server stores, embeds, retrieves, and mutates documents. It does not make business decisions. |
| Agent-owned reasoning | Deduplication, prioritization, classification, and merging belong to AI agents using MCP tools. |
| Generic tools | Keep the MCP surface small and document-shaped. Avoid domain-specific tools. |
| Single container | Use one Cosmos DB container and discriminate by `docType`. |
| Permissive payloads | Favor flexible JSON payloads over rigid tables. Unknown client fields should survive round-trip storage. |
| Server-owned embeddings | Clients send text, not vectors. Embeddings are generated inside the server. |
| Partition by user | Keep `userId` even in single-user MVP so the storage shape does not need to change later. |
| Deployability first | Runtime design must match the Azure deployment model documented here. |

## 3. Scope and Non-Goals

### In scope

- MCP server with `stdio` and `streamable-http` transports
- Azure Container Apps deployment
- Azure Cosmos DB for NoSQL with vector search
- Microsoft Foundry backed embedding generation
- CRUD, query, vector search, and read-only raw query operations

### Out of scope

- Multi-user identity design beyond the existing `userId` partition key
- Server-side deduplication, prioritization, merging, or classification
- Calendar sync, web UI, or Telegram bot logic
- Server-side taxonomy enforcement for tags

Expected dedup pattern:
- agents call `search` before writing new memory-like documents
- the agent decides whether to create, update in place, or skip
- the MCP server never enforces similarity thresholds or uniqueness rules

## 4. System Architecture

### Runtime topology

1. External agents and clients connect to the MCP server over `stdio` or `streamable-http`.
2. The server validates documents, generates embeddings where configured, and writes to Cosmos DB.
3. Search requests embed the query text, execute Cosmos vector search, and return ranked results.
4. The server never returns the raw embedding array to callers.

### Hosting model

| Component | Target |
|---|---|
| MCP server | Azure Container Apps |
| Data store | Azure Cosmos DB for NoSQL |
| Embeddings | Microsoft Foundry / Azure OpenAI models |
| Container image | Shared Azure Container Registry |
| Observability | Log Analytics via Container Apps environment |

### Transport

| Mode | Use case | Command |
|---|---|---|
| `stdio` | Local development with CLI tools | `python -m openbrain --transport stdio` |
| `streamable-http` | Azure Container Apps | `python -m openbrain --transport streamable-http --host 0.0.0.0 --port 8000 --path /mcp` |

`stateless_http=True` is required for hosted `streamable-http` because Azure Container Apps can scale to zero and route requests to any replica.

## 5. Data Architecture

### Storage model

Use a single Cosmos DB container:
- Database: `openbrain`
- Container: `openbrain-data`
- Partition key: `/userId`

Current MVP document classes:
- `memory`
- `idea`
- `task`
- `goal`
- `misc`
- `userSettings`

### Taxonomy boundaries

- `memory`: factual or reference information you want to recall later
- `idea`: speculative, generative, or not-yet-committed thoughts you want to revisit later
- `task`: discrete actions with a finite completion loop
- `goal`: ongoing objectives or areas of progress, distinct from discrete tasks
- `misc`: ambiguous or under-specified captures that should be preserved without forced classification
- `userSettings`: per-user configuration documents stored alongside content in the same partition

Important decisions:
- `fact` is not a separate `docType`; facts live in `memory`
- `review` is not an MVP `docType`
- `reminder` is not a stored entity; reminders are agent behavior layered on top of tasks and goals
- ambiguous or low-confidence captures can be stored as `misc`
- the user-managed tag taxonomy is stored in Cosmos as a `userSettings` document

### Common fields

| Field | Type | Source | Notes |
|---|---|---|---|
| `id` | `string` | Server | Format: `{docType}:{uuid4}` |
| `userId` | `string` | Server | Partition key |
| `docType` | `string` | Client | `memory`, `idea`, `task`, `goal`, `misc`, or `userSettings` |
| `narrative` | `string` | Client | Main human-readable text. Required for content docs; not used by `userSettings`. |
| `embedding` | `float[]` | Server | Present only on embedded document classes and never returned to clients |
| `rawText` | `string` | Client optional | Original brain dump, stored but not returned |
| `contextTags` | `string[]` | Client optional | Lightweight taxonomy tags such as `personal`, `soligence`, or `microsoft` |
| `aiMetadata` | `AiMetadata` | Client optional | AI-generated metadata |
| `createdAt` | `string` | Server | ISO 8601 UTC |
| `updatedAt` | `string` | Server | ISO 8601 UTC |

Immutable from client updates:
- `id`
- `userId`
- `docType`
- `createdAt`
- `embedding`

### Pydantic model configuration

Both `BaseDocument` and `AiMetadata` are configured with `extra="allow"`. Any JSON fields not explicitly declared in the schema are accepted during validation and stored as-is in Cosmos DB. This supports forward compatibility: clients can attach additional metadata fields without requiring server-side schema changes.

### Tagging

Tagging is intentionally lightweight:
- tags live in `contextTags`
- tags should come from a user-managed taxonomy to avoid uncontrolled sprawl
- the initial seeded taxonomy is `personal`, `soligence`, and `microsoft`
- the AI can add or refine tags over time
- tags support organization and filtering without requiring a rigid server-enforced schema

Taxonomy storage:
- the allowed or preferred user tag taxonomy is stored in a per-user `userSettings` document
- content documents reference tags through `contextTags`
- the server stores the taxonomy but does not hard-enforce it during writes in MVP

### AiMetadata sub-schema

| Field | Type | Default | Notes |
|---|---|---|---|
| `urgency` | `"high"` \| `"medium"` \| `"low"` \| `null` | `null` | AI-assessed urgency level |
| `inferredEntities` | `string[]` | `[]` | Entity names extracted by the AI |

Model configuration: `extra="allow"` - unknown fields sent by clients are preserved.

### Memory documents

Current baseline:
- `memory` is the factual and reference-recall document family
- memories are embedded and searched semantically
- evolving truths such as passwords or account details are handled by agent-driven in-place updates

Required:
- `docType = "memory"`
- `narrative`

Optional:
- `hypotheticalQueries`: `string[]` - 3 future questions this narrative answers, used for HyDE embedding quality (default: `[]`)

### Idea documents

Current baseline:
- `idea` captures speculative, generative, or not-yet-committed thoughts
- examples include product ideas, feature ideas, business ideas, and exploratory concepts
- ideas are preserved for later recall and refinement rather than treated as factual truth

Required:
- `docType = "idea"`
- `narrative`

Optional:
- `goalId`: `string | null` - optional link to a related goal (default: `null`)

### Task documents

Current baseline:
- `task` is for discrete actions with a finite completion loop
- the MVP task classes are one-time and recurring tasks
- reminders are agent behavior layered on top of task state, not a separate stored entity
- tasks may contribute toward a goal and can link back to it through `goalId`

Required:
- `docType = "task"`
- `narrative`
- `taskType`: `"oneTimeTask"` | `"recurringTask"`

Optional:
- `goalId`: `string | null` - optional link to a related goal (default: `null`)
- `state`: `TaskState` object (default: `TaskState()` with `status = "open"`)

#### TaskState sub-schema

| Field | Type | Default | Notes |
|---|---|---|---|
| `status` | `"open"` \| `"inProgress"` \| `"done"` \| `"cancelled"` \| `"deferred"` | `"open"` | Current lifecycle status |
| `dueDate` | `string \| null` | `null` | ISO 8601 UTC |
| `isRecurring` | `bool` | `false` | Whether the task repeats |
| `recurrenceDays` | `int \| null` | `null` | Days between recurrences |
| `lastCompletedAt` | `string \| null` | `null` | ISO 8601 UTC |
| `completionCount` | `int` | `0` | Incremented on each completion |
| `progressNotes` | `string[]` | `[]` | Append-only log of progress entries |

For operational "what is coming up?" views, recurring tasks should have an explicit `dueDate`. `recurrenceDays` by itself defines cadence, but it does not establish the next upcoming occurrence unless the task has either:
- an explicit seeded `dueDate`, or
- a prior completion event that allowed the server to compute the next `dueDate`

#### `recurrenceDays` conversion table

`recurrenceDays` is an integer representing calendar days between recurrences. The triage agent converts natural-language expressions before calling `write`.

| Expression | `recurrenceDays` |
|---|---|
| weekly | `7` |
| biweekly | `14` |
| monthly | `30` |
| quarterly | `90` |
| every 6 months | `180` |
| yearly | `365` |

The server performs no interpretation of this field beyond recurring-task completion behavior.

#### Recurring task completion logic

When a recurring task's `state.status` is set to `"done"` via `update`, the server executes these steps:

1. Increment `state.completionCount` by 1.
2. Set `state.lastCompletedAt` to the current UTC timestamp.
3. Compute `state.dueDate` as `now + state.recurrenceDays` days.
4. Reset `state.status` to `"open"`.
5. Append a completion note to `state.progressNotes`.

Trigger conditions:
- the update sets `state.status` to `"done"`
- the existing `state.isRecurring` is `true`
- the existing `state.recurrenceDays` is defined and non-null
- the existing `state.status` is not already `"done"`

All recurrence counts forward from completion date, not from the original due date. Calendar-anchored events belong in an external calendar system, not Open Brain.

#### Retention policy

Completed (one-time) and cancelled tasks are retained indefinitely. There is no server-side TTL or auto-pruning. Keeping historical tasks enables agents to answer questions like "what did I accomplish this month?" and supports pattern analysis over time. Agents may delete individual tasks explicitly if cleanup is desired, but the default is to keep everything.

### Goal documents

Current baseline:
- `goal` is distinct from `task`
- goals represent ongoing objectives or areas of progress rather than discrete checklist items
- reminders for stale goals are agent behavior, not a separate stored entity
- one purpose of the system is to help agents break goals down into tasks and track progress over time

Required:
- `docType = "goal"`
- `narrative`

Optional:
- `state`: `GoalState` object (default: `GoalState()` with `status = "active"`)

#### GoalState sub-schema

| Field | Type | Default | Notes |
|---|---|---|---|
| `status` | `"active"` \| `"paused"` \| `"completed"` \| `"abandoned"` | `"active"` | Goal lifecycle state |
| `targetDate` | `string \| null` | `null` | ISO 8601 UTC |
| `lastProgressAt` | `string \| null` | `null` | ISO 8601 UTC |
| `progressNotes` | `string[]` | `[]` | Append-only log of progress updates |

### Ambiguous intake handling

Current baseline:
- `review` is not an MVP document type
- ambiguous or low-confidence captures can be stored as `misc`
- the agent may also ask for clarification outside this repo when that orchestration exists

### Misc documents

Current baseline:
- `misc` is the catch-all intake type for ambiguous, under-specified, or not-yet-classified captures
- `misc` exists so the system can preserve uncertain input without forcing a premature classification decision
- agents are expected to revisit `misc` items and convert them into better-typed documents over time
- `misc` is query-only until reclassified and is not embedded for semantic search

Required:
- `docType = "misc"`
- `narrative`

Optional:
- `triageNotes`: `string | null` - brief note about why the item remained ambiguous (default: `null`)
- `suggestedDocType`: `string | null` - best current guess such as `task`, `goal`, `memory`, or `idea` (default: `null`)

### User settings documents

Current baseline:
- `userSettings` stores per-user configuration in the same Cosmos container and partition model
- it is not embedded and is not part of semantic search
- the initial use case is storing the user-managed tag taxonomy

Required:
- `docType = "userSettings"`
- `id = "userSettings:{userId}"`

Optional:
- `tagTaxonomy`: `string[]` - user-managed preferred tags such as `personal`, `soligence`, and `microsoft`
- `behaviorPreferences`: `BehaviorPreferences | null` - user-shaped agent behavior controls
- additional user-scoped config fields may be added later under the same document

#### BehaviorPreferences sub-schema

This document family is the preferred place to persist user-shaped behavior controls for the agent layer.

These fields define stored preference signals, not product-mandated defaults for outreach timing. External agents may interpret them conservatively or evolve them over time.

| Field | Type | Default | Notes |
|---|---|---|---|
| `proactivityLevel` | `"low"` \| `"medium"` \| `"high"` | `"medium"` | Overall system assertiveness |
| `dailyCheckInEnabled` | `bool` | `false` | Whether lightweight check-ins are desired |
| `weeklyPlanningEnabled` | `bool` | `false` | Whether planning summaries are desired |
| `staleGoalNudgeDays` | `int \| null` | `null` | Optional implementation hint for stale-goal resurfacing |
| `ideaResurfacingDays` | `int \| null` | `null` | Optional implementation hint for idea resurfacing |
| `confirmationSensitivity` | `"low"` \| `"medium"` \| `"high"` | `"medium"` | How readily the agent should ask before structural changes |
| `coachingDirectness` | `"light"` \| `"balanced"` \| `"strong"` | `"balanced"` | Tone/intensity of proactive guidance |

Implementation guidance:
- these are preferences for external agents and clients layered on top of OpenBrain
- the MCP server stores them but does not enforce them as business logic
- agents should read them and adapt outreach, prompting, and confirmation behavior accordingly
- implementations should avoid treating these fields as rigid schedule contracts unless the user explicitly wants that

## 6. Embeddings and Vector Search

### Embedding model

| Setting | Value |
|---|---|
| Provider | Microsoft Foundry / Azure OpenAI |
| Model deployment | `text-embedding-3-large` |
| Vector dimensions | 3072 |
| Distance function | `cosine` |

`text-embedding-3-large` is the default target for MVP.

Current architecture decision:
- use the `openai` Python package with the `OpenAI` client
- use OpenAI v1 endpoints
- do not use the Responses API for embeddings
- use API key authentication for embeddings for now

### Runtime client contract

The implementation target for embeddings is the OpenAI v1 API.

The server stores the Foundry resource base endpoint in `AI_FOUNDRY_ENDPOINT` and normalizes it to an OpenAI v1 base URL at runtime.

Accepted base endpoint shapes:
- `https://<resource>.services.ai.azure.com/`
- `https://<resource>.openai.azure.com/`

Canonical implementation choice:
- prefer the `OpenAI` client over `AzureOpenAI`
- use `client.embeddings.create(...)` for embeddings
- do not model embeddings around the Responses API
- keep API key auth as the MVP path because current Microsoft docs still document API key auth for embeddings with OpenAI v1

Implementation target:

```python
from openai import OpenAI

base_url = Config.AI_FOUNDRY_ENDPOINT.rstrip("/")
if not base_url.endswith("/openai/v1"):
    base_url = f"{base_url}/openai/v1/"

client = OpenAI(
    api_key=Config.AI_FOUNDRY_API_KEY,
    base_url=base_url,
)

response = client.embeddings.create(
    model=Config.AI_FOUNDRY_EMBEDDING_DEPLOYMENT,
    input="text to embed",
    encoding_format="float",
)
embedding = response.data[0].embedding
```

### HyDE strategy

For `memory` documents with `hypotheticalQueries`:
1. Embed the `narrative`.
2. Embed each hypothetical query.
3. Average the vectors element-wise.
4. Store the averaged vector as `embedding`.

For all other embedded documents, embed the `narrative` directly.

### Embedding scope

Semantic search is intentionally narrower than the full document store.

Current decision:
- `memory` and `idea` are the primary embedded and searchable document classes
- `task`, `goal`, and `misc` are operational records first and should be handled through `query`
- if a future use case proves it necessary, task or goal embeddings can be added later

When a search result contains `hypotheticalQueries`, the server logs them at `DEBUG` level for search quality analysis. `hypotheticalQueries` is still stripped from results.

### Cosmos vector score semantics

`VectorDistance()` with cosine distance returns a similarity score, not a raw distance. The server aliases the result as `score` and returns it directly with no post-processing.

Callers should treat `score` as a ranking signal:
- higher is better
- ranking matters more than absolute thresholds

### Cosmos container policy

The container must be created with a vector embedding policy and vector index at creation time.

```json
{
  "id": "openbrain-data",
  "partitionKey": {
    "paths": ["/userId"],
    "kind": "Hash",
    "version": 2
  },
  "vectorEmbeddingPolicy": {
    "vectorEmbeddings": [
      {
        "path": "/embedding",
        "dataType": "float32",
        "dimensions": 3072,
        "distanceFunction": "cosine"
      }
    ]
  },
  "indexingPolicy": {
    "indexingMode": "consistent",
    "automatic": true,
    "includedPaths": [
      { "path": "/*" }
    ],
    "excludedPaths": [
      { "path": "/embedding/*" },
      { "path": "/rawText/?" },
      { "path": "/_etag/?" }
    ],
    "vectorIndexes": [
      {
        "path": "/embedding",
        "type": "diskANN"
      }
    ]
  }
}
```

Notes:
- `diskANN` is the chosen vector index type
- vector indexes are immutable after container creation
- vector search requires the account capability `EnableNoSQLVectorSearch`

## 7. MCP Tool Surface

The server exposes exactly seven tools:

| Tool | Purpose |
|---|---|
| `write` | Create a document, generate embedding, set timestamps |
| `read` | Read one document by ID |
| `query` | Structured filter-based query |
| `search` | Vector similarity search |
| `update` | Partial update with dot-path support |
| `delete` | Hard delete |
| `raw_query` | Read-only Cosmos SQL for advanced cases |

### Tool behavior requirements

#### `write`

- validates the document against the Pydantic model class for the given `docType`
- valid MVP document models are `MemoryDocument`, `IdeaDocument`, `TaskDocument`, `GoalDocument`, `MiscDocument`, and `UserSettingsDocument`
- returns field-level validation detail when validation fails
- generates `id`, `userId`, `createdAt`, `updatedAt`, and `embedding` for document types that participate in semantic search
- ignores client attempts to set server-owned fields
- returns `{"status": "created", "id": ..., "docType": ...}`

#### `read`

- requires `userId` and `id`
- returns the document without internal fields such as `embedding` and `rawText`

#### `query`

- supports `docType` filter
- supports dot-path equality filters such as `{"state.status": "open"}`
- supports `sortBy` with default `"createdAt"`
- supports `sortDesc` with default `true`
- supports `limit` in the range `1..100`, default `50`
- uses the caller `userId` partition
- `null` filter values match fields that are missing or null
- this is the primary tool for operational views such as open tasks, active goals, or life-state dumps
- returns `{"results": [...], "total": <count>}`

#### `search`

- requires `query` as natural language search text
- supports optional `docType` filter
- supports `topK` in the range `1..20`, default `5`
- embeds the query text at runtime
- uses Cosmos vector search on `/embedding`
- searches only document classes intentionally embedded for semantic recall
- returns ranked results with `score`
- logs `hypotheticalQueries` at debug level when matched memory documents have them
- never returns `embedding`, `rawText`, or `hypotheticalQueries`

Example response shape:

```json
{
  "results": [
    {
      "id": "memory:abc-123",
      "docType": "memory",
      "narrative": "The garage router password is admin/Netgear2024.",
      "contextTags": ["home", "network"],
      "aiMetadata": { "urgency": "low" },
      "score": 0.94,
      "createdAt": "2026-03-11T14:30:00Z"
    }
  ],
  "query": "garage router password",
  "total": 1
}
```

#### `update`

- requires `id` and `updates`
- supports dot-path updates for nested fields
- ignores immutable fields
- regenerates the embedding if `narrative` or `hypotheticalQueries` changes on an embedded document
- applies recurring-task completion logic when a recurring task is marked done
- returns `{"id": ..., "status": "updated", "updatedAt": ...}`

#### `delete`

- hard deletes by `id` and `userId`

#### `raw_query`

- read-only Cosmos SQL only
- client SQL must include `c.userId = @userId` in the `WHERE` clause
- the server injects the `@userId` parameter automatically
- clients may supply additional parameters
- results are capped at `100`
- results are sanitized to remove `embedding` and `rawText`

## 8. Configuration

### Required environment variables

| Variable | Purpose |
|---|---|
| `COSMOS_HOST` | Cosmos account endpoint |
| `COSMOS_KEY` | Cosmos primary key for current bootstrap |
| `COSMOS_DATABASE` | Database name |
| `COSMOS_CONTAINER` | Container name |
| `AI_FOUNDRY_ENDPOINT` | Foundry resource base endpoint |
| `AI_FOUNDRY_API_KEY` | Foundry / Azure OpenAI API key |
| `AI_FOUNDRY_EMBEDDING_DEPLOYMENT` | Embedding deployment name |
| `DISABLE_AUTH` | Enable MVP dev-mode auth bypass |
| `DEFAULT_USER_ID` | User ID used when auth is disabled |
| `ENVIRONMENT` | `dev`, `prod`, or `test` |
| `LOG_LEVEL` | Application logging level |
| `PORT` | HTTP port |

### Example `.env`

```ini
# Cosmos DB
COSMOS_HOST=https://your-cosmos-account.documents.azure.com:443/
COSMOS_KEY=your-cosmos-primary-key
COSMOS_DATABASE=openbrain
COSMOS_CONTAINER=openbrain-data

# Azure AI Foundry
AI_FOUNDRY_ENDPOINT=https://your-resource.services.ai.azure.com/
AI_FOUNDRY_API_KEY=your-api-key
AI_FOUNDRY_EMBEDDING_DEPLOYMENT=text-embedding-3-large

# Auth
DISABLE_AUTH=true
DEFAULT_USER_ID=dev-user

# Server
ENVIRONMENT=dev
LOG_LEVEL=INFO
PORT=8000
```

### Auth stance

Current implementation target:
- dev mode may use `DISABLE_AUTH=true`
- hosted production should move toward managed identity and secretless access where possible

First hardening targets after MVP:
1. managed identity for Azure-hosted workloads
2. Key Vault or managed secret references
3. removal of raw API keys from app env vars where Azure supports it

## 9. Infrastructure and Deployment

### Azure resources

| Resource | Name pattern | Notes |
|---|---|---|
| Resource Group | `rg-openbrain-{env}` | Per-environment |
| Log Analytics Workspace | `log-openbrain-{env}` | Required by Container Apps environment |
| Container Registry | Shared services ACR | Pre-existing shared resource, not provisioned by this repo |
| Container Apps Environment | `openbrain-env-{env}` | Shared hosted environment |
| Cosmos DB Account | `openbrain-cosmos-{env}-{suffix}` | Serverless by default |
| Foundry resource | `ob{env}{suffix}` | `Microsoft.CognitiveServices/accounts`, kind `AIServices` |
| Foundry project | `openbrain-{env}` | Child `accounts/projects` resource |
| Container App | `openbrain-mcp-{env}` | External HTTP ingress, target port 8000 |

### Hosting requirements

- Container App listens on port `8000`
- ingress target port must be `8000`
- MCP endpoint path is `/mcp`
- min replicas can be `0`
- max replicas can start at `1`

### Foundry resource provisioning

Canonical IaC model:
- `Microsoft.CognitiveServices/accounts`
- `Microsoft.CognitiveServices/accounts/projects`

The Foundry resource and project are provisioned separately from model deployments. Model deployment creation is an explicit step and must not be assumed to exist automatically.

### Deployment workflow

Required deployment order:

1. Validate infrastructure changes with `az deployment group what-if`.
2. Provision Azure infrastructure owned by this repo: resource group, Log Analytics, Container Apps environment, serverless Cosmos account and container, Foundry resource and project, and the Container App.
3. Reuse the shared-services ACR instead of creating a new registry in this repo's resource group.
4. Create the `text-embedding-3-large` model deployment on the Foundry resource if it does not already exist.
5. Build and push the container image to the shared ACR.
6. Create or update the Container App.
7. Apply secrets and environment variables after the Container App exists.
8. Smoke test the hosted `/mcp` endpoint.

### Deployment scripts

| Script | Purpose |
|---|---|
| `deployment/common.ps1` | Shared Azure CLI helpers and deployment state management |
| `deployment/setup-infrastructure.ps1` | Resource group, Log Analytics, Container Apps environment, serverless Cosmos, vector-enabled container, and Foundry resource and project |
| `deployment/deploy.ps1` | Build image in the shared ACR and create or update the Container App |
| `deployment/set-env-vars.ps1` | Set Container App secrets and env vars; validate embedding deployment exists |

### Operational requirements

- Cosmos account mode defaults to `serverless`
- Cosmos vector capability must be enabled before container creation
- Foundry model deployment must exist before app secrets and env vars are applied
- shared ACR lives outside this resource group's ownership and is treated as an input dependency
- deployment validation must include a preflight step, not only best-effort create or update

## 10. Error Handling

### Exception hierarchy

All custom exceptions inherit from a single base class:

```text
OpenBrainError
|- CosmosDBError
|- EmbeddingError
|- DocumentNotFoundError
|- ValidationError
|- AuthenticationError
\- ConfigurationError
```

The tool layer catches all exceptions and returns `{"error": ...}`. Errors never propagate to the MCP transport.

### Response shape

Errors return a simple JSON object:

```json
{ "error": "Document 'memory:abc-123' not found" }
```

Validation errors can include details:

```json
{
  "error": "Validation error",
  "details": ["narrative is required"]
}
```

## 11. Testing Strategy

### Unit tests

Use mocked Cosmos and embedding clients to validate:
- model validation and defaults
- document write behavior
- update behavior
- recurring-task completion logic
- embedding generation and HyDE averaging
- search result sanitization

### Integration tests

Use a real test environment when available to validate:
- Cosmos container policy compatibility
- vector search query behavior
- Foundry embedding calls
- MCP transport behavior over both `stdio` and HTTP

### Deployment validation

Each environment rollout should validate:
- Bicep compilation
- `az deployment group what-if`
- infrastructure provisioning
- model deployment existence
- Container App health
- `/mcp` endpoint smoke test

## 12. Outstanding Decisions

The following items are still intentionally open:
- whether goals need additional structured fields beyond `GoalState`
