# OpenBrain Migration Items

Purpose: curated content to import into OpenBrain.

This document is intentionally limited to migration data. It does not define rollout mechanics, prompt rewrites, cron behavior, or file deprecation steps.

## Import Target

- userId: `dan@soligenceadvisors.com`
- docTypes in scope:
  - `task`
  - `goal`
  - `memory`
  - `idea`
  - `userSettings`
- taxonomy seed for `userSettings.tagTaxonomy`:
  - `personal`
  - `soligence`
  - `microsoft`

Note: "facts" should be imported as `memory`, not as a separate docType.

## userSettings

```json
{
  "docType": "userSettings",
  "tagTaxonomy": [
    "personal",
    "soligence",
    "microsoft"
  ]
}
```

## Tasks

| Ref | narrative | contextTags | taskType | status | dueDate | isRecurring | recurrenceDays | notes |
|---|---|---|---|---|---|---|---|---|
| T2 | GHCP SDK project | `microsoft` | oneTimeTask | done |  | false |  | Submitted 2026-03-08 |
| T4 | Mail state taxes | `personal` | oneTimeTask | open |  | false |  | Federal done, state still needs mailing |
| T5 | Setup car remote start | `personal` | oneTimeTask | open |  | false |  |  |
| T6 | Setup Christmas gifts (Meta smart glasses, floor lamp, video desk camera) | `personal` | oneTimeTask | open |  | false |  |  |
| T7 | Core lifts schedule - commit to basement routine | `personal` | oneTimeTask | open |  | false |  |  |
| T8 | Set up calendar reminders via AI assistant | `personal` | oneTimeTask | open |  | false |  |  |
| T9 | Car registration renewal | `personal` | recurringTask | open | 2026-04-15 | true | 365 | Annual renewal. Expires 2026-05-26 |
| T10 | Car insurance renewal | `personal` | recurringTask | open | 2026-04-15 | true | 180 | Allstate |
| T12 | Copilot + MCP guide | `microsoft` | oneTimeTask | open |  | false |  | From Prism |
| T13 | Printer ink | `personal` | oneTimeTask | open |  | false |  | From Prism |
| T14 | Professional teeth whitening | `personal` | oneTimeTask | open |  | false |  | From Prism |
| T15 | RX refill | `personal` | recurringTask | open |  | true | 30 | Monthly recurring. From Prism |
| T16 | Install new Ring doorbell | `personal` | oneTimeTask | open |  | false |  | From Prism |
| T17 | Install or fix garage door opener | `personal` | oneTimeTask | open |  | false |  | From Prism |
| T18 | Seasonal wardrobe review and donations | `personal` | recurringTask | open | 2026-07-01 | true | 180 | Spring and Fall. From Prism |
| T19 | Go through mail | `personal` | recurringTask | open |  | true | 7 | Weekly. From Prism |
| T20 | Update all phone apps to new phone | `personal` | oneTimeTask | open |  | false |  | From Prism |

## Goals

| Ref | narrative | contextTags | status | targetDate | progressNotes |
|---|---|---|---|---|---|
| G1 | Half-marathon: knock 25 minutes off current time | `personal` | active | 2026-11-01 |  |
| G2 | Diet: lose 15 lbs; connect to mental clarity and confidence, not guilt | `personal` | active | 2026-08-01 | Good progress, already losing as of 2026-03-08 |
| G3 | Hair consultation: find high-end Philadelphia salon for new style and gradual color | `personal` | active |  |  |
| G4 | Spanish learning: every few days, flexible format | `personal` | active |  |  |
| G5 | Instagram: build photo collection with elevated lifestyle narrative | `personal` | active | 2026-12-31 |  |
| G6 | Improve dating life: ultimate goal behind appearance, fitness, and confidence improvements | `personal` | active |  |  |
| G7 | Patio project: evaluating 3 contractors, targeting fall 2026 or spring 2027 | `personal` | active |  | Yardzen design #3 received 2026-03-08; decided timeline fall 2026 or spring 2027; evaluating 3 contractors |

## Memories

| Ref | narrative | contextTags | hypotheticalQueries |
|---|---|---|---|
| M1 | Fitness routine: 3-4x per week yoga and weights, intermittent fasting is an established practice, home gym in basement | `personal` | What is my workout routine?; Do I have a home gym?; What diet do I follow? |
| M2 | Mailbox location: Box 3, Slot #16 | `personal` | Where is my mailbox?; What is my mailbox number? |
| M3 | Electrical room: clicking sound is likely a dying power adapter for the coax extender; watch for failure | `personal` | What's the clicking sound in the electrical room?; Is there a known issue with the coax? |
| M4 | Home finance: sewer bill is my responsibility, not escrow. Property tax is paid by escrow and Citadel gets a copy. If the house is reassessed, expect an extra bill that escrow may not receive and I am liable for it. | `personal` | Who pays the sewer bill?; Is property tax in escrow?; What happens if the house is reassessed? |

## Ideas

| Ref | narrative | contextTags |
|---|---|---|
| I1 | Article: AI Problem Categories - framework for which classes of problems AI can and cannot solve. Categories: effort problems, coordination problems, emotional intelligence, judgment and willpower, domain expertise, ambiguity. Could differentiate Soligence positioning by targeting the right problem class. | `soligence` |
| I2 | Reddit pain point to MVP pipeline - systematic approach to finding real user pain points on Reddit and building MVPs to address them | `soligence` |
| I3 | Idea vetting and research tool - structured process for evaluating and researching business or product ideas | `soligence` |
| I4 | Enterprise agent bindings for subscriptions - binding enterprise agents to subscription-based managed services | `soligence` |
| I5 | AI output rejection tracking - capture and encode when AI output is rejected to build signal on failure patterns, identify blind spots, and improve prompts, agent config, and model selection | `soligence` |
| I6 | Teleprompter feature for Soligence presentations repo | `soligence` |
