"""Seed a small representative dataset into a live OpenBrain deployment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import anyio
from fastmcp import Client


PILOT_DOCUMENTS: list[dict[str, Any]] = [
    {
        "docType": "memory",
        "narrative": (
            "Fitness routine: 3-4x per week yoga and weights, intermittent fasting is "
            "an established practice, home gym in basement"
        ),
        "rawText": (
            "Fitness routine: 3-4x per week yoga and weights, intermittent fasting is "
            "an established practice, home gym in basement"
        ),
        "contextTags": ["personal", "fitness"],
        "hypotheticalQueries": [
            "What is Dan's workout routine?",
            "Does Dan have a home gym?",
            "What diet does Dan follow?",
        ],
        "migrationRef": "M1",
        "migrationSource": "openbrain-migration-items.md",
    },
    {
        "docType": "memory",
        "narrative": "Mailbox location: Box 3, Slot #16",
        "rawText": "Mailbox location: Box 3, Slot #16",
        "contextTags": ["personal"],
        "hypotheticalQueries": [
            "Where is Dan's mailbox?",
            "What is the mailbox number?",
        ],
        "migrationRef": "M2",
        "migrationSource": "openbrain-migration-items.md",
    },
    {
        "docType": "idea",
        "narrative": (
            "Article: AI Problem Categories - framework for which classes of problems AI "
            "can and cannot solve. Categories: effort problems, coordination problems, "
            "emotional intelligence, judgment and willpower, domain expertise, ambiguity. "
            "Could differentiate Soligence positioning by targeting the right problem class."
        ),
        "rawText": (
            "Article: AI Problem Categories - framework for which classes of problems AI "
            "can and cannot solve. Categories: effort problems, coordination problems, "
            "emotional intelligence, judgment and willpower, domain expertise, ambiguity. "
            "Could differentiate Soligence positioning by targeting the right problem class."
        ),
        "contextTags": ["soligence", "thought-leadership"],
        "migrationRef": "I1",
        "migrationSource": "openbrain-migration-items.md",
    },
    {
        "docType": "goal",
        "narrative": "Half-marathon: knock 25 minutes off current time",
        "rawText": "Half-marathon: knock 25 minutes off current time",
        "contextTags": ["personal", "fitness"],
        "state": {
            "status": "active",
            "targetDate": "2026-11-01",
            "progressNotes": [],
        },
        "migrationRef": "G1",
        "migrationSource": "openbrain-migration-items.md",
    },
    {
        "docType": "task",
        "narrative": "Mail state taxes",
        "rawText": "Mail state taxes",
        "contextTags": ["personal"],
        "taskType": "oneTimeTask",
        "state": {
            "status": "open",
            "isRecurring": False,
            "progressNotes": ["Federal done, state still needs mailing"],
        },
        "migrationRef": "T4",
        "migrationSource": "openbrain-migration-items.md",
    },
]

USER_SETTINGS_DOC = {
    "docType": "userSettings",
    "tagTaxonomy": [
        "personal",
        "soligence",
        "microsoft",
        "fitness",
        "thought-leadership",
    ],
    "migrationSource": "openbrain-migration-items.md",
}


def load_state(environment: str) -> dict[str, Any]:
    state_path = Path("deployment/.state") / f"{environment}.json"
    return json.loads(state_path.read_text())


async def ensure_user_settings(client: Client) -> None:
    existing = await client.call_tool("query", {"docType": "userSettings", "limit": 5})
    existing_docs = existing.data.get("results", [])
    if not existing_docs:
        created = await client.call_tool("write", {"document": USER_SETTINGS_DOC})
        print(f"created userSettings: {created.data['id']}")
        return

    doc = existing_docs[0]
    current_tags = list(doc.get("tagTaxonomy", []))
    merged_tags: list[str] = []
    seen: set[str] = set()
    for tag in current_tags + USER_SETTINGS_DOC["tagTaxonomy"]:
        lowered = str(tag).strip().lower()
        if lowered and lowered not in seen:
            seen.add(lowered)
            merged_tags.append(lowered)

    if merged_tags != current_tags:
        updated = await client.call_tool(
            "update",
            {
                "id": doc["id"],
                "updates": {
                    "tagTaxonomy": merged_tags,
                    "migrationSource": USER_SETTINGS_DOC["migrationSource"],
                },
            },
        )
        print(f"updated userSettings: {updated.data['id']}")
    else:
        print(f"skipped userSettings: {doc['id']}")


async def ensure_document(client: Client, document: dict[str, Any]) -> None:
    lookup = await client.call_tool(
        "query",
        {
            "docType": document["docType"],
            "filters": {"narrative": document["narrative"]},
            "limit": 5,
        },
    )
    matches = lookup.data.get("results", [])
    if matches:
        print(f"skipped {document['migrationRef']}: {matches[0]['id']}")
        return

    created = await client.call_tool("write", {"document": document})
    print(f"created {document['migrationRef']}: {created.data['id']}")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", default="dev")
    parser.add_argument("--url", default="")
    parser.add_argument("--token", default="")
    args = parser.parse_args()

    state = load_state(args.environment)
    url = args.url or f"https://{state['containerAppFqdn']}/mcp"
    token = args.token or state["openBrainApiToken"]

    client = Client(url, auth=token)
    async with client:
        await ensure_user_settings(client)
        for document in PILOT_DOCUMENTS:
            await ensure_document(client, document)


if __name__ == "__main__":
    anyio.run(main)
