# Open Brain: System Blueprint

## The Vision

Open Brain is a frictionless, AI-native "second brain" designed for a complex life—juggling a full-time job, a business, and personal/home upkeep. Traditional productivity apps fail because they demand too much manual data entry. Open Brain solves this by letting you simply text or voice-note your thoughts into Telegram, trusting an AI agent to organize, remember, and remind you of things automatically.

It is designed to bridge the gap between **remembering** (knowledge) and **doing** (productivity).

## The User Experience (How it feels)

### 1. The Frictionless Brain Dump

Throughout the day, you text or send voice notes to your Open Brain via Telegram. You don't use tags, you don't select due dates from a calendar UI, you just brain dump.

> "I need to pay my overdue urology bill."

> "The VIN for the Lexus is 12345ABC."

> "Remind me to do my taxes quarterly."

The system instantly accepts these messages, getting them out of your head so you can move on.

### 2. The Evening Ping (State Reconciliation)

Instead of making you open a to-do app to check off boxes, the system proactively manages its own state. Every evening, it sends you a message: "What did you accomplish today?" You reply naturally: "I paid that urology bill and spent an hour learning Spanish." The AI agent reads this, finds the relevant tasks or goals in your system, and marks them as done or updates your progress.

### 3. Contextual Recall

When you need information, you just ask. "How do I reset the garage router?" The system retrieves the exact discrete facts you dictated months ago and responds conversationally.

### 4. Intelligent Prioritization & Planning

While recurring tasks and reminders count down in the background automatically, you are never left staring at a massive, overwhelming list of chores. The AI agent acts as your Chief of Staff. By leveraging massive 1-million+ token context windows, it ingests your entire life state at once—looking at deterministic countdowns, upcoming meetings, open to-do lists, operational business needs, and neglected personal goals. It synthesizes all of this to proactively help you prioritize your day and plan your week.

### 5. The Weekly Sync (Human-in-the-Loop)

Not everything can or should be automated. Ambiguous brain dumps, complex goal realignments, or items that need human intuition are queued up for a once-a-week review. You can clear this queue iteratively over a voice conversation with the AI, or visually via a dynamic web UI.

## Under the Hood (How it works)

Behind the scenes, an asynchronous AI "Triage Agent" constantly watches your incoming brain dumps and sorts them into two distinct memory systems based on what the data actually is.

### Infrastructure & Deployment

- **The Brain (Cloud):** The actual data (Azure Cosmos DB for NoSQL with vector search) and a Model Context Protocol (MCP) server live in the cloud. This ensures your life state is universally accessible to any authorized AI tool (like the Claude desktop app) anywhere you go.

- **The Muscle (Flexible LLM):** The AI Triage Agent that processes the Telegram messages can be run locally (e.g., on a Mac Mini) for maximum privacy, or via a cloud API, hooking into the cloud data via the MCP server.

### System A: Semantic Memory (The Vector Store)

This is for unstructured, static information. It's built for natural language search. The Triage Agent sends data here if it is:

- **Discrete Facts & Info:** Reference data you'll need later. (e.g., House build year, refrigerator make/model, router reset instructions).
- **Loose Ideas:** Shower thoughts or brainstorms that don't have actionable steps yet. (e.g., "Idea for a new life management app").

### System B: Deterministic State (The Task Engine)

This is for stateful, actionable items that need to be tracked, scheduled, or completed. The Triage Agent extracts the relevant dates/frequencies and sends data here if it is:

- **Focus Areas & Goals:** Broad objectives to track over time. (e.g., "Learn to speak Spanish").
- **One-Time To-Dos:** Specific actions with a definitive end state. (e.g., "Pay urology bill").
- **Recurring Tasks:** Chores on a set cadence. (e.g., "Deep clean the shower monthly," "Renew car registration every 6 months").
- **Reminders:** Proactive alerts based on time or lack of progress. (e.g., "No progress on learning Spanish in 3 weeks," or "Quarterly taxes are due").

### Triage Agent Operations

**Deduplication & Cleanup Sweeps:** During triage, the AI cross-references the incoming brain dump with existing tasks to prevent nagging duplicates (e.g., merging "Pay the urology bill" and "Urology bill is due Friday" into one updated task). It also runs periodic background sweeps to clean up the database. This includes managing "evolving truths"—recognizing when a new fact (e.g., a new router password) supersedes an old one in the vector store, allowing the system to archive stale data.

## The Golden Rules of the System

- **The AI/Determinism Balance:** The system relies on rigid, deterministic code for things that need absolute precision (like a quarterly tax reminder counting down), but it uses fluid AI for orchestration. The AI sits on top of the deterministic engine to help you prioritize, plan, and pivot based on the reality of your schedule.

- **Permissive Data:** We do not force data into rigid database columns. The AI uses flexible JSON or narrative schemas to store information so it never crashes just because a brain dump was formatted weirdly.

- **Proactive, Not Passive:** The system shouldn't wait for you to check it. Between the Evening Ping, intelligent prioritization, and reminders for "stale" goals, the system should actively help you keep your life on track.

## Aspirational Features (Future Roadmap)

**Behavioral Meta-Learning:** Eventually, the system should learn *how* you work, not just *what* you need to do. By capturing behavioral patterns over time (e.g., noticing you consistently push a Wednesday recurring chore to Saturday), the AI can adapt its scheduling recommendations to match your actual psychological routines, rather than rigidly adhering to initial estimates.
