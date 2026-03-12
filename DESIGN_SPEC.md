# Open Brain: Technical Design Specification

> Version: 3.2
> Date: 2026-03-12
> Status: Baseline for implementation — interview decisions restored
> Repository: `openbrain`

## 1. Purpose

Open Brain is an MCP server that stores personal life-state documents, generates embeddings, and serves retrieval/query/update operations to external agents and clients.

This repo owns the server and its deployment surface.

This repo does not own:
- Telegram ingestion
- Triage, deduplication, prioritization, or cleanup reasoning
- Human-facing UI
- External schedulers and orchestrators

## 2. Core Principles

| Principle | Implication |
|---|---|
| Server = data layer | The server stores, embeds, retrieves, and mutates documents. It does not make business decisions. |
| Generic tools | Keep the MCP surface small and document-shaped. Avoid domain-specific tools. |
| Single container | Use one Cosmos DB container and discriminate by `docType`. |
| Permissive payloads | Favor flexible JSON payloads over rigid tables. `BaseDocument` and `AiMetadata` use Pydantic `extra="allow"` so unknown fields sent by clients are accepted and preserved on round-trip. |
| Server-owned embeddings | Clients send text, not vectors. Embeddings are generated inside the server. |
| Partition by user | Keep `userId` even in single-user MVP so the storage shape does not have to change later. |
| Deployability first | The implementation must match the Azure deployment model documented here. |

## 3. Scope and Non-Goals

### In scope
- MCP server with `stdio` and `streamable-http` transports
- Azure Container Apps deployment
- Azure Cosmos DB for NoSQL with vector search
- Microsoft Foundry backed embedding generation
- CRUD, query, vector search, and raw read-only query operations

### Out of scope
- Multi-user identity design beyond the existing `userId` partition key
- Server-side deduplication or prioritization
  > **Expected dedup pattern:** Agents are responsible for deduplication. Before writing a new document, agents should call `search` with the candidate narrative to check for near-duplicates. The agent decides whether to write a new document, update an existing one, or skip. The server provides retrieval tools but does not enforce uniqueness or similarity thresholds.
- Calendar sync, web UI, or Telegram bot logic
- Server-side taxonomy enforcement for tags

## 4. System Architecture

### Runtime topology

1. External agents and clients connect to the MCP server over `stdio` or `streamable-http`.
2. The server validates documents, generates embeddings, and writes to Cosmos DB.
3. Search requests embed the query text, execute Cosmos vector search, and return ranked results.
4. The server never returns the raw embedding array to callers.

### Hosting model

| Component | Target |
|---|---|
| MCP server | Azure Container Apps |
| Data store | Azure Cosmos DB for NoSQL |
| Embeddings | Microsoft Foundry / Azure OpenAI models |
| Container image | Azure Container Registry |
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

Supported document classes:
- `memory`
- `task`
- `review`

### Common fields

| Field | Type | Source | Notes |
|---|---|---|---|
| `id` | `string` | Server | Format: `{docType}:{uuid4}` |
| `userId` | `string` | Server | Partition key |
| `docType` | `string` | Client | `memory`, `task`, or `review` |
| `narrative` | `string` | Client | Main human-readable text used for embeddings |
| `embedding` | `float[]` | Server | Never returned to clients |
| `rawText` | `string` | Client optional | Original brain dump, stored but not returned |
| `contextTags` | `string[]` | Client optional | Not used for filtering in MVP |
| `aiMetadata` | `AiMetadata` | Client optional | AI-generated metadata (see AiMetadata sub-schema below) |
| `createdAt` | `string` | Server | ISO 8601 UTC |
| `updatedAt` | `string` | Server | ISO 8601 UTC |

Immutable from client updates:
- `id`
- `userId`
- `docType`
- `createdAt`
- `embedding`

#### Pydantic model configuration

Both `BaseDocument` and `AiMetadata` are configured with `extra="allow"`. Any JSON fields not explicitly declared in the schema are accepted during validation and stored as-is in Cosmos DB. This supports forward compatibility: clients can attach additional metadata fields without requiring server-side schema changes.

#### AiMetadata sub-schema

| Field | Type | Default | Notes |
|---|---|---|---|
| `urgency` | `"high"` \| `"medium"` \| `"low"` \| `null` | `null` | AI-assessed urgency level |
| `inferredEntities` | `string[]` | `[]` | Entity names extracted by the AI |

Model configuration: `extra="allow"` — unknown fields sent by clients are preserved.

### Memory documents

Required:
- `docType = "memory"`
- `narrative`
- `memoryType`: `"fact"` | `"idea"` — classifies the memory

Optional:
- `hypotheticalQueries`: `string[]` — 3 future questions this narrative answers, used for HyDE embedding quality (default: `[]`)
- `supersededBy`: `string | null` — `id` of the document that replaces this one, set by cleanup agents (default: `null`)

### Task documents

Required:
- `docType = "task"`
- `narrative`
- `taskType`: `"goal"` | `"oneTimeTask"` | `"recurringTask"` — classifies the task

Optional:
- `state`: `TaskState` object (default: `TaskState()` with `status = "open"`)

#### TaskState sub-schema

| Field | Type | Default | Notes |
|---|---|---|---|
| `status` | `"open"` \| `"inProgress"` \| `"done"` \| `"cancelled"` \| `"deferred"` | `"open"` | Current lifecycle status |
| `dueDate` | `string \| null` | `null` | ISO 8601 UTC |
| `isRecurring` | `bool` | `false` | Whether the task repeats |
| `recurrenceDays` | `int \| null` | `null` | Days between recurrences (see conversion table) |
| `lastCompletedAt` | `string \| null` | `null` | ISO 8601 UTC |
| `completionCount` | `int` | `0` | Incremented on each completion |
| `progressNotes` | `string[]` | `[]` | Append-only log of progress entries |

#### `recurrenceDays` conversion table

`recurrenceDays` is an integer representing calendar days between recurrences. The Triage Agent converts natural-language expressions before calling `write`:

| Expression | `recurrenceDays` |
|---|---|
| weekly | `7` |
| biweekly | `14` |
| monthly | `30` |
| quarterly | `90` |
| every 6 months | `180` |
| yearly | `365` |

The server performs no interpretation of this field — it stores and returns the integer as-is.

#### Recurring task completion logic

When a recurring task's `state.status` is set to `"done"` via `update`, the server executes these steps:

1. **Increment** `state.completionCount` by 1
2. **Set** `state.lastCompletedAt` to the current UTC timestamp
3. **Compute** `state.dueDate` as `now + state.recurrenceDays` days
4. **Reset** `state.status` to `"open"`
5. **Append** a completion note (`"Completed on YYYY-MM-DD"`) to `state.progressNotes`

**No-op guard:** If the task's `state.status` is already `"done"`, setting it to `"done"` again has no effect.

**Trigger conditions** (all must be true):
- The update sets `state.status` to `"done"`
- The existing `state.isRecurring` is `true`
- The existing `state.recurrenceDays` is defined and non-null
- The existing `state.status` is not already `"done"`

All recurrence counts down from **completion date**, not from the original due date. Calendar-anchored events (rent on the 1st, taxes on April 15) belong in Google Calendar, not Open Brain.

### Review documents

Required:
- `docType = "review"`
- `narrative`

Optional:
- `triageAttempt`: `object` — free-form record of the triage agent's reasoning (default: `{}`)
- `resolution`: `"reIngested"` | `"discarded"` | `null` — outcome of the review (default: `null`)
- `resolvedAt`: `string | null` — ISO 8601 UTC timestamp of resolution (default: `null`)

## 6. Embeddings and Vector Search

### Embedding model

| Setting | Value |
|---|---|
| Provider | Microsoft Foundry / Azure OpenAI |
| Model deployment | `text-embedding-3-large` |
| Vector dimensions | 3072 |
| Distance function | `cosine` |

`text-embedding-3-large` is the current default target because it is the highest-quality embedding model in the current Azure OpenAI / Foundry catalog.

### Runtime client contract

The implementation target is the OpenAI v1 API.

The server stores the Foundry resource base endpoint in `AI_FOUNDRY_ENDPOINT` and normalizes it to an OpenAI v1 base URL at runtime.

Accepted base endpoint shapes:
- `https://<resource>.services.ai.azure.com/`
- `https://<resource>.openai.azure.com/`

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
1. Embed the `narrative`
2. Embed each hypothetical query
3. Average the vectors element-wise
4. Store the averaged vector as `embedding`

For all other documents, embed the `narrative` directly.

When a search result contains `hypotheticalQueries`, the server logs them at `DEBUG` level for search quality analysis. This does not affect the response — `hypotheticalQueries` is still stripped from results.

### Cosmos vector score semantics

`VectorDistance()` with cosine distance returns a **similarity** score, not a raw distance. The return range for cosine is `-1` (least similar) to `+1` (most similar).

The server aliases the result as `score` in the query and returns it directly with no post-processing.

Callers should treat `score` as a ranking signal:
- higher is better (more similar)
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
- `diskANN` is a graph-based approximate nearest neighbor index that scales to millions of vectors while maintaining high recall. It handles both small and large datasets well.
- Both `quantizedFlat` and `diskANN` require at least 1,000 vectors before the index activates. Below that threshold Cosmos performs a full scan regardless.
- Vector indexes are immutable after container creation — choosing diskANN now avoids a future migration if the dataset grows.
- Vector search requires the account capability `EnableNoSQLVectorSearch`.

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
- Validates the document against the Pydantic model class for the given `docType` (`MemoryDocument`, `TaskDocument`, or `ReviewDocument`)
- Pydantic validation errors are returned to the client with field-level detail (location and message for each error)
- Generates `id` (format `{docType}:{uuid4}`), `userId`, timestamps (`createdAt`, `updatedAt`), and `embedding`
- Ignores client attempts to set server-owned fields
- Returns `{"status": "created", "id": ..., "docType": ...}`

#### `read`
- Requires `userId` and `id`
- Returns the document without internal fields such as `embedding` and `rawText`

#### `query`
- Supports `docType` filter
- Supports dot-path equality filters (e.g., `{"state.status": "open"}`)
- Supports `sortBy` (dot-path field name, default `"createdAt"`)
- Supports `sortDesc` (boolean, default `true`)
- Supports `limit` (integer, range 1-100, default 50; clamped to bounds)
- Uses the caller `userId` partition
- `null` filter values match documents where the field is undefined or null
- Returns `{"results": [...], "total": <count>}`

#### `search`
- Requires `query` (natural language search text)
- Supports optional `docType` filter
- Supports `topK` (integer, range 1-20, default 5; clamped to bounds)
- Embeds the query text at runtime
- Uses Cosmos vector search on `/embedding`
- Returns ranked results with `score` (cosine similarity, higher = more similar)
- Logs `hypotheticalQueries` at debug level when matched documents have them (search quality observability)
- Never returns `embedding`, `rawText`, or `hypotheticalQueries`

Example response shape:

```json
{
  "results": [
    {
      "id": "memory:abc-123",
      "docType": "memory",
      "memoryType": "fact",
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
- Requires `id` (document ID) and `updates` (dict of fields to change)
- Supports dot-path updates for nested fields (e.g., `{"state.status": "done"}` changes only `state.status`, preserving all other `state` fields)
- Ignores immutable fields (`id`, `userId`, `docType`, `createdAt`, `embedding`)
- Regenerates the embedding if `narrative` or `hypotheticalQueries` changes
- Applies recurring-task completion logic when a recurring task is marked done (see Section 5, "Recurring task completion logic")
- Returns `{"id": ..., "status": "updated", "updatedAt": ...}`

#### `delete`
- Hard deletes by `id` and `userId`

#### `raw_query`
- Read-only Cosmos SQL only (no DELETE, UPDATE, or INSERT)
- The client SQL **must** include `c.userId = @userId` in the WHERE clause
- The server injects the `@userId` parameter automatically — clients must not include it in the `parameters` list
- Client may supply additional parameters via the `parameters` list (e.g., `[{"name": "@status", "value": "open"}]`)
- Results are capped at 100 items
- Returns sanitized results without `embedding` or `rawText`

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
- Dev mode may use `DISABLE_AUTH=true`
- Hosted production should move toward managed identity and secretless access where possible

The first secure hardening target after MVP is:
1. managed identity for Azure-hosted workloads
2. Key Vault or managed secret references
3. removal of raw API keys from app env vars where Azure supports it

## 9. Infrastructure and Deployment

### Azure resources

| Resource | Name pattern | Notes |
|---|---|---|
| Resource Group | `rg-openbrain-{env}` | Per-environment |
| Log Analytics Workspace | `log-openbrain-{env}` | Required by Container Apps environment |
| Container Registry | `openbrain{env}{suffix}` | Globally unique; Basic SKU in current bootstrap |
| Container Apps Environment | `openbrain-env-{env}` | Shared hosted environment |
| Cosmos DB Account | `openbrain-cosmos-{env}-{suffix}` | Serverless by default |
| Foundry resource | `ob{env}{suffix}` | `Microsoft.CognitiveServices/accounts`, kind `AIServices` |
| Foundry project | `openbrain-{env}` | Child `accounts/projects` resource |
| Container App | `openbrain-mcp-{env}` | External HTTP ingress, target port 8000 |

### Hosting requirements

- Container App listens on port `8000`
- Ingress target port must be `8000`
- MCP endpoint path is `/mcp`
- Min replicas can be `0` for cost efficiency
- Max replicas can start at `1` for MVP and be raised later

### Foundry resource provisioning

The canonical IaC model is:
- `Microsoft.CognitiveServices/accounts`
- `Microsoft.CognitiveServices/accounts/projects`

The Foundry resource and project are provisioned separately from model deployments.

Model deployment creation is an explicit step and must not be assumed to exist automatically.

### Deployment workflow

Required deployment order:

1. Provision Azure infrastructure.
2. Run `az deployment group what-if` before any Bicep `create` step.
3. Create or validate the `text-embedding-3-large` model deployment on the Foundry resource.
4. Build and push the container image.
5. Create or update the Container App.
6. Apply secrets and environment variables after the Container App exists.
7. Smoke test the hosted `/mcp` endpoint.

### Deployment scripts

| Script | Purpose |
|---|---|
| `deployment/common.ps1` | Shared Azure CLI helpers and deployment state management |
| `deployment/setup-infrastructure.ps1` | Resource group, Log Analytics, ACR, Container Apps environment, serverless Cosmos, vector-enabled container, optional Foundry resource/project |
| `deployment/deploy.ps1` | Build image in ACR and create/update the Container App |
| `deployment/set-env-vars.ps1` | Set Container App secrets and env vars; validate embedding deployment exists |

### Operational requirements

- Cosmos account mode defaults to `serverless`
- Cosmos vector capability must be enabled before container creation
- Foundry model deployment must exist before app secrets/env vars are applied
- Deployment validation must include a preflight step, not only best-effort create/update

### Security notes

Current bootstrap is acceptable for dev:
- Cosmos key injected as Container App secret
- Foundry key injected as Container App secret

Preferred production hardening path:
- managed identity for data-plane access where supported
- Key Vault-backed secret management
- remove ACR admin credential dependency
- restrict public network access where feasible

## 10. Error Handling

### Exception hierarchy

All custom exceptions inherit from a single base class:

```
OpenBrainError                          # Base exception for all Open Brain errors
├── CosmosDBError                       # Error during Cosmos DB operations
├── EmbeddingError                      # Error during embedding generation
├── DocumentNotFoundError               # Requested document does not exist
├── ValidationError                     # Document data validation failed
├── AuthenticationError                 # Authentication failed
└── ConfigurationError                  # Invalid configuration
```

The tool layer catches all exceptions and returns `{"error": ...}` — errors never propagate to the MCP transport.

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
- update merge logic
- recurring task completion behavior
- search response sanitization
- search score pass-through semantics
- raw query sanitization

### Integration tests

Use a real Azure dev subscription because the local emulator does not support the hosted vector-search path needed here.

Integration coverage target:
- vector-enabled container creation
- write + search round trip
- recurring task update
- hosted Container App `/mcp` reachability
- env var and secret injection

### Deployment smoke tests

After each hosted deployment:
1. confirm the Container App revision is healthy
2. confirm `/mcp` responds
3. write one memory
4. search for it semantically
5. confirm returned results exclude `embedding`

## 12. Implementation Order

### Phase 1: Server correctness

1. Finalize the runtime client shape for OpenAI v1 against the Foundry endpoint.
2. Fix vector score handling so the server passes through Cosmos score semantics directly.
3. Align container indexing policy with the documented vector policy.
4. Ensure tool responses strip internal fields consistently.

### Phase 2: Deployment correctness

1. Add `what-if` preflight for Bicep-backed deployment steps.
2. Add model deployment creation or validation automation.
3. Tighten Container App deployment and secret wiring.
4. Add smoke-test commands for hosted verification.

### Phase 3: Agent integration

1. Point triage and cleanup agents at the hosted MCP endpoint.
2. Validate end-to-end write/search workflows from an external agent.
3. Add operational docs for recurring runs and cleanup jobs.

## 13. Appendix: Canonical Cosmos Search Query

```sql
SELECT TOP @topK
    c.id,
    c.docType,
    c.narrative,
    c.contextTags,
    c.aiMetadata,
    c.createdAt,
    c.updatedAt,
    c.memoryType,
    c.taskType,
    c.state,
    c.supersededBy,
    c.triageAttempt,
    c.resolvedAt,
    c.resolution,
    c.hypotheticalQueries,
    VectorDistance(c.embedding, @queryVector) AS score
FROM c
WHERE c.userId = @userId
ORDER BY VectorDistance(c.embedding, @queryVector)
```

Server response requirements for search:
- strip `embedding`
- strip `rawText`
- strip `hypotheticalQueries`
- expose the Cosmos vector score as `score`
