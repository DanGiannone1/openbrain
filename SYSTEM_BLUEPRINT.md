# Open Brain: System Blueprint

## The Vision

Open Brain is a frictionless, AI-native "second brain" designed for a complex life, juggling a full-time job, a business, and personal/home upkeep. Traditional productivity apps fail because they demand too much manual data entry. Open Brain solves this by letting you simply text or voice-note your thoughts into Telegram, trusting an AI agent to organize, remember, and remind you of things automatically.

It is designed to bridge the gap between remembering and doing.

## The User Experience

### 1. The Frictionless Brain Dump

Throughout the day, you text or send voice notes to your Open Brain via Telegram. You do not use tags or pick dates from a UI. You just brain dump.

> "I need to pay my overdue urology bill."

> "The VIN for the Lexus is 12345ABC."

> "Remind me to do my taxes quarterly."

The system instantly accepts these messages, getting them out of your head so you can move on.

### 2. The Evening Ping

Instead of making you open a to-do app to check off boxes, the system proactively manages its own state. Every evening, it can send you a message such as: "What did you accomplish today?" You reply naturally: "I paid that urology bill and spent an hour learning Spanish." The AI agent reads this, finds the relevant tasks or goals in your system, and updates state accordingly.

### 3. Contextual Recall

When you need information, you just ask. "How do I reset the garage router?" The system retrieves the exact reference information you dictated months ago and responds conversationally.

### 4. Intelligent Prioritization and Planning

While recurring tasks and reminders count down in the background automatically, you are never left staring at a massive, overwhelming list of chores. The AI agent acts as your Chief of Staff. By leveraging large context windows, it can look at deterministic countdowns, open tasks, business needs, and neglected personal goals all at once. It synthesizes that state to help you prioritize your day and plan your week.

### 5. The Weekly Sync

Not everything can or should be automated. Ambiguous brain dumps can be preserved as `misc` until a later cleanup pass or weekly review. Complex goal realignments and fuzzy planning still benefit from human judgment, whether through a voice conversation with the AI or a future UI.

## Under the Hood

Behind the scenes, an asynchronous AI triage agent watches incoming brain dumps and routes them into a small set of document types based on what the data actually is.

### Infrastructure and Deployment

- The cloud brain: Azure Cosmos DB for NoSQL with vector search plus an MCP server hosted in Azure Container Apps.
- The model layer: Microsoft Foundry backed embeddings for semantic recall.
- The muscle: external agents and orchestrators that reason over the data using MCP tools.

### Semantic Recall

The semantic layer is for unstructured information built for natural-language retrieval:

- `memory`: reference information you will want later, such as credentials, VINs, procedures, or home details.
- `idea`: speculative, generative, or not-yet-committed thoughts worth preserving and revisiting later.

### Deterministic State

The operational layer is for stateful items that need to be tracked over time:

- `goal`: broad objectives that require sustained progress.
- `task`: concrete work items, either one-time or recurring.
- `misc`: ambiguous captures that should be preserved without forced classification.

Reminders are not a stored document type. They are agent behavior layered on top of goals and tasks.

### Triage and Cleanup Operations

The MCP server remains a data layer. Agents do the reasoning. Triage agents classify raw input, cleanup agents look for duplicates or stale records, taxonomy maintainers normalize tags, and goal maintainers keep long-running goals actionable.

For evolving truths such as passwords or account details, cleanup updates the existing memory in place rather than maintaining supersession chains in the server schema.

## Golden Rules

- The server stores, embeds, queries, and updates documents. It does not decide what matters.
- Agents own classification, prioritization, cleanup, and reminder logic.
- The schema should stay flexible enough to preserve weird or incomplete input without breaking.
- The system should be proactive, not passive.

## Future Direction

Over time, Open Brain can learn more about behavior, not just state. That includes better prioritization, adaptive cadence suggestions, and richer planning loops. Those capabilities should sit on top of the stored data, not inside the core MCP server contract.
