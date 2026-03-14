# OpenBrain: User Journeys and Behavioral Requirements

## Purpose

This document captures the expected user-facing and agent-facing behavior of OpenBrain.

Use it to answer:
- what the user should be able to do
- what the agent should do on the user's behalf
- what proactive behavior is desirable
- what "good" looks like for the system

This is not the implementation contract. For exact schemas, API/tool behavior, and server rules, use [DESIGN_SPEC.md](C:/projects/openbrain/DESIGN_SPEC.md).

## Document Role

Use the top-level docs like this:
- [USER_JOURNEYS.md](C:/projects/openbrain/USER_JOURNEYS.md): expected behavior and requirements
- [DESIGN_SPEC.md](C:/projects/openbrain/DESIGN_SPEC.md): implementation contract
- [SYSTEM_BLUEPRINT.md](C:/projects/openbrain/SYSTEM_BLUEPRINT.md): product context and conceptual framing

If a journey here is desired but not yet reflected in the design spec, update the design spec before changing code.

## Core Jobs To Be Done

OpenBrain should help the user:
- get things out of their head quickly
- remember facts and reference information later
- preserve ideas worth revisiting
- track one-time and recurring tasks without heavy manual workflow
- keep goals visible without turning the system into a rigid productivity app
- receive useful, low-friction prompts or reminders when appropriate

## High-Level System Responsibilities

This section is the highest-level answer to "what should this system do for the user?"

### User asks / user does

OpenBrain should let the user:
- capture facts, ideas, goals, and tasks with very little friction
- ask natural-language questions about their life, work, home, and business state
- review what is open, what is upcoming, and what has changed
- update progress naturally rather than through a rigid form workflow
- complete recurring tasks and have the system keep the cycle moving
- revisit ideas and goals without losing context

### Agent asks / agent does

OpenBrain-supporting agents should help by:
- triaging raw user input into the right document type
- lightly cleaning captured text while preserving the original raw input
- deduplicating or updating memories and ideas when appropriate
- helping the user workshop goals into concrete next steps when invited
- helping keep records organized and coherent over time
- surfacing neglected, stale, or important state without surprising the user

### Proactive support the overall system may provide

At a high level, the overall system should be able to:
- remind the user about upcoming recurring tasks and deadlines
- notice things that have fallen off the radar
- help the user stay on track with goals
- support weekly planning by looking holistically at goals, tasks, and commitments
- support lightweight daily check-ins or progress updates
- help the user decide what matters this week without becoming overbearing

## Desired Capability Areas

These are the major buckets of expected behavior we should design around.

### 1. Capture and externalize

The system should make it easy to get information out of the user's head and into stable storage.

### 2. Recall and answer

The system should reliably answer questions about what the user has previously captured.

### 3. Track and maintain state

The system should maintain clear operational state for tasks, recurring responsibilities, and goals.

### 4. Organize and refine

The system should help keep the knowledge base clean, coherent, and easy to use over time.

### 5. Coach and keep on track

The system should help the user make progress on goals, not just store them passively.

### 6. Prompt and remind

The system should provide useful proactive outreach when something is upcoming, stale, or worth revisiting.

### 7. Support planning and reflection

The system should help with weekly planning, prioritization, and lightweight reflection based on everything it knows.

## Product Behavior Map

This section translates the high-level capability areas into concrete product behavior modes.

For the current phase of OpenBrain, the bias should be:
- start more active rather than too passive
- allow the system to be opinionated and helpful
- tune down later if behavior feels noisy or unhelpful

The main user is currently the product owner, architect, and developer, so the system does not need to be overly timid at this stage.

### 1. Core system behavior

These behaviors are foundational and should always be strong:
- capture quickly
- classify effectively
- preserve raw input
- maintain lightly cleaned stored text
- retrieve the right memory or idea later
- track tasks and goals reliably
- roll recurring tasks forward correctly

### 2. Reminder behavior

The system should proactively surface:
- upcoming recurring tasks
- overdue one-time tasks
- tasks that are still open after a meaningful amount of time
- time-sensitive obligations that are approaching

Examples:
- "Your car registration renewal is due soon."
- "You still have `Mail state taxes` open."
- "Your prescription refill is coming up."

### 3. Check-in behavior

The system should be able to ask for lightweight updates in order to keep state fresh.

Examples:
- "What did you get done today?"
- "Did you end up mailing the state taxes?"
- "Did you refill your prescription?"

Purpose:
- close the loop on stale or uncertain state
- keep the second brain aligned with reality

### 4. Weekly planning behavior

The system should be able to step back and help the user decide what matters for the coming week.

Examples:
- "Here are the top 3 things to focus on this week."
- "You have a mix of admin, home, and work items that need attention."
- "These are the goals and tasks that seem most important right now."

Purpose:
- reduce overwhelm
- provide prioritization help
- make the system feel like a lightweight chief of staff

### 5. Goal support behavior

The system should help the user stay connected to goals over time.

Examples:
- "You have not made progress on Spanish in a while."
- "Your patio project has not been updated recently."
- "This goal may need a next step or a decision."

Important nuance:
- the system should support goals actively
- but it should not silently create surprise tasks or hidden work
- suggestions and prompts are good
- hidden autonomous task creation is not

### 6. Idea resurfacing behavior

The system should periodically revive good ideas that have gone cold.

Examples:
- "You captured several Soligence ideas that you have not revisited."
- "This idea may be worth reviewing again."
- "You have multiple related ideas that could be grouped together."

Purpose:
- keep valuable thinking from getting buried
- make the idea store feel alive, not archival

### 7. Pattern insight behavior

The system should eventually notice patterns across everything it knows.

Examples:
- "You have been handling urgent admin work, but none of your longer-term goals moved this week."
- "Most of your recent activity has been personal; Microsoft and Soligence items may need attention."
- "You keep revisiting this same category of task or idea."

Purpose:
- give the user higher-order insight
- move from storage toward useful reflection and guidance

### 8. Prioritization behavior

The system should be able to synthesize:
- urgency
- deadlines
- neglected goals
- recurring obligations
- broader personal, business, and work context

It should then produce useful recommendations such as:
- what to focus on today
- what to focus on this week
- what is slipping
- what can wait

### 9. Behavioral posture

The intended posture is:
- proactive
- helpful
- willing to nudge
- not constrained by fear of seeming "too active" during this early phase

That said, the system still should not:
- fabricate urgency
- make hidden changes
- create surprise tasks
- alter important state without a reason that could be explained to the user

## Action Authority Model

OpenBrain should separate proactive outreach from structural change.

### Automatic actions

These are safe to surface automatically when grounded in real state:
- due soon reminders
- overdue reminders
- recurring-task reminders
- stale goal nudges
- stale idea resurfacing
- weekly planning summaries
- daily or near-daily check-ins
- contextual recall during active conversations

### Confirmation-first actions

These should normally be suggested first and applied only after the user agrees:
- creating new tasks from a goal
- linking tasks to goals
- turning a vague thought into a goal or task with higher commitment
- retagging or reorganizing important records
- updating an existing memory when the change is meaningful but not obvious
- applying a proposed weekly focus plan as actual state changes

### Never-do-silently actions

These should never happen without explicit user approval:
- deleting records
- creating surprise obligations
- materially changing due dates
- cancelling or abandoning goals or tasks
- destructive merges
- reclassifying important records in a way the user would find surprising

## Behavior Preferences And Adaptation

The system should let the user shape behavior over time rather than forcing one fixed personality.

### Preference areas

The user should be able to tune:
- how proactive the system is
- how often reminders are sent
- whether daily check-ins are wanted
- whether weekly planning is wanted
- how often stale goals should be resurfaced
- how often ideas should be resurfaced
- how assertive the agent should be when suggesting next steps
- when the system should ask before making structural changes

### Preference learning

The system should also learn from repeated user feedback such as:
- "be more proactive"
- "stop reminding me about this so often"
- "ask me before creating tasks"
- "surface ideas more often"
- "weekly planning is useful"

Over time, the system should become better calibrated to the user's real tolerance and preferences without drifting into hidden autonomous behavior.

## User-Initiated Journeys

The sections below break the system down into more concrete flows. Treat them as examples and operating journeys, not the full high-level requirement set by themselves.

### 1. Capture a memory

User behavior:
- the user says something they want remembered
- examples:
  - "My mailbox is Box 3 Slot 16"
  - "The sewer bill is not paid through escrow"

Expected system behavior:
- the agent classifies it as a `memory`
- the system stores it with minimal friction
- later recall queries should retrieve it reliably

Good outcome:
- the user can later ask naturally and get the right memory back

### 2. Capture an idea

User behavior:
- the user captures a business, product, or life idea they want to revisit later

Expected system behavior:
- the agent classifies it as an `idea`
- the idea is preserved without forcing excessive structure
- the user can later search or ask for relevant ideas

Good outcome:
- ideas are easy to capture and easy to rediscover

### 3. Create a one-time task

User behavior:
- the user states a discrete action
- example: "Mail state taxes"

Expected system behavior:
- the agent classifies it as a one-time `task`
- the task starts in an open state unless the user says otherwise
- the user can later query open tasks and mark it done

Good outcome:
- one-time tasks feel lightweight and obvious

### 4. Create a recurring task

User behavior:
- the user states a repeating responsibility or routine
- examples:
  - "Refill my prescription every month"
  - "Go through mail every week"

Expected system behavior:
- the agent creates a recurring `task`
- `recurrenceDays` captures cadence
- `dueDate` captures the next upcoming occurrence
- if the user does not provide an initial due date, the system should initialize one from creation time plus `recurrenceDays`

Good outcome:
- the user can ask what is coming up soon and recurring tasks participate correctly

### 5. Complete a recurring task

User behavior:
- the user says they completed the recurring task

Expected system behavior:
- the task is marked complete
- the system automatically rolls the next `dueDate` forward by `recurrenceDays`
- the task returns to an open state for the next cycle

Good outcome:
- recurring tasks continue cleanly without requiring recreation

### 6. Ask a memory recall question

User behavior:
- the user asks a natural-language recall question
- examples:
  - "What is my mailbox number?"
  - "Who pays the sewer bill?"

Expected system behavior:
- the system searches memories semantically
- the correct memory should rank highly, ideally first

Good outcome:
- the user trusts the system as a recall layer

### 7. Review tasks and goals

User behavior:
- the user asks:
  - what open tasks exist
  - what recurring tasks are coming up
  - what active goals exist

Expected system behavior:
- tasks and goals are queryable directly
- recurring tasks can be surfaced by upcoming `dueDate`
- the user can update, complete, or clarify items

Good outcome:
- operational state is visible without feeling like a traditional to-do app

## Agent-Initiated Journeys

### 1. Triage raw input

Agent behavior:
- interpret ambiguous user input
- classify it into the smallest correct document type
- preserve raw input where helpful

Expected constraint:
- classification is agent behavior, not server behavior

### 2. Deduplicate or update memories

Agent behavior:
- search before writing a new memory or idea
- decide whether to create a new document or update an existing one in place

Expected constraint:
- the server does not deduplicate automatically

### 3. Keep state organized

Agent behavior:
- normalize tags
- keep data coherent
- help maintain clean records over time

Expected constraint:
- organization help is allowed
- the system should not silently create new user work without explicit intent

### 4. Support goals without overreaching

Agent behavior:
- help the user think through goals
- optionally propose next steps
- help link tasks to goals when the user wants that

Expected constraint:
- the system should not auto-generate hidden or surprise tasks just because a goal exists

## Proactive Outreach Patterns

These are desirable behaviors for external agents or clients layered on top of OpenBrain.

### Helpful proactive prompts

Examples:
- "Your car registration renewal is due on April 15, 2026."
- "You still have `Mail state taxes` open."
- "You have not updated your patio project in a while. Do you want to review it?"
- "Your RX refill is coming up soon."

### Good proactive behavior

- relevant
- infrequent enough not to feel spammy
- grounded in actual stored state
- framed as assistance, not nagging

### Bad proactive behavior

- creating tasks the user did not ask for
- inventing urgency without evidence
- noisy reminders with no clear action value
- changing records in ways the user would find surprising

## Non-Goals

OpenBrain should not:
- become a full project-management system
- require the user to micromanage tags and forms
- auto-create surprise work from vague heuristics
- hide important state transitions from the user
- turn the MCP server into the planning or orchestration engine

## Acceptance Lens

The system is behaving well when:
- capture is fast
- recall is accurate
- recurring tasks roll forward correctly
- one-time tasks stay simple
- goals are visible without causing hidden automation
- proactive outreach feels useful rather than intrusive

## Open Questions To Revisit

- how much proactive outreach is actually helpful in practice
- whether `misc` stays valuable or becomes unnecessary
- when a goal should merely be visible versus when an agent should suggest a next step
- whether recurring tasks with no real-world deadline should still get seeded `dueDate`s by default
