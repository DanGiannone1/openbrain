"""Seed OpenBrain from the curated migration items markdown document."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import anyio
from fastmcp import Client


def load_state(environment: str) -> dict[str, Any]:
    state_path = Path("deployment/.state") / f"{environment}.json"
    return json.loads(state_path.read_text())


def _extract_section(markdown: str, heading: str) -> str:
    marker = f"## {heading}"
    start = markdown.find(marker)
    if start == -1:
        raise ValueError(f"Section '{heading}' not found in migration document.")

    start += len(marker)
    remainder = markdown[start:]
    next_heading = remainder.find("\n## ")
    if next_heading == -1:
        return remainder.strip()
    return remainder[:next_heading].strip()


def _extract_json_block(section: str) -> dict[str, Any]:
    start = section.find("```json")
    if start == -1:
        raise ValueError("JSON block not found.")
    start += len("```json")
    end = section.find("```", start)
    if end == -1:
        raise ValueError("JSON block terminator not found.")
    return json.loads(section[start:end].strip())


def _parse_markdown_table(section: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in section.splitlines() if line.strip().startswith("|")]
    if len(lines) < 2:
        return []

    headers = [cell.strip() for cell in lines[0].strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in lines[2:]:
        values = [cell.strip() for cell in line.strip("|").split("|")]
        if len(values) != len(headers):
            raise ValueError(f"Malformed table row: {line}")
        rows.append(dict(zip(headers, values, strict=True)))
    return rows


def _parse_tags(value: str) -> list[str]:
    if not value:
        return []
    tags: list[str] = []
    for part in value.split(","):
        cleaned = part.replace("`", "").strip().lower()
        if cleaned:
            tags.append(cleaned)
    return tags


def _parse_list(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(";") if item.strip()]


def _none_if_blank(value: str) -> str | None:
    cleaned = value.strip()
    return cleaned or None


def _parse_bool(value: str) -> bool:
    return value.strip().lower() == "true"


def load_documents_from_markdown(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    markdown = path.read_text(encoding="utf-8")
    source_name = path.name

    user_settings = _extract_json_block(_extract_section(markdown, "userSettings"))
    user_settings["migrationSource"] = source_name

    tasks: list[dict[str, Any]] = []
    for row in _parse_markdown_table(_extract_section(markdown, "Tasks")):
        notes = _parse_list(row["notes"])
        task: dict[str, Any] = {
            "docType": "task",
            "narrative": row["narrative"],
            "rawText": row["narrative"],
            "contextTags": _parse_tags(row["contextTags"]),
            "taskType": row["taskType"],
            "state": {
                "status": row["status"],
                "dueDate": _none_if_blank(row["dueDate"]),
                "isRecurring": _parse_bool(row["isRecurring"]),
                "recurrenceDays": int(row["recurrenceDays"]) if _none_if_blank(row["recurrenceDays"]) else None,
                "progressNotes": notes,
            },
            "migrationRef": row["Ref"],
            "migrationSource": source_name,
        }
        tasks.append(task)

    goals: list[dict[str, Any]] = []
    for row in _parse_markdown_table(_extract_section(markdown, "Goals")):
        goal: dict[str, Any] = {
            "docType": "goal",
            "narrative": row["narrative"],
            "rawText": row["narrative"],
            "contextTags": _parse_tags(row["contextTags"]),
            "state": {
                "status": row["status"],
                "targetDate": _none_if_blank(row["targetDate"]),
                "progressNotes": _parse_list(row["progressNotes"]),
            },
            "migrationRef": row["Ref"],
            "migrationSource": source_name,
        }
        goals.append(goal)

    memories: list[dict[str, Any]] = []
    for row in _parse_markdown_table(_extract_section(markdown, "Memories")):
        memory: dict[str, Any] = {
            "docType": "memory",
            "narrative": row["narrative"],
            "rawText": row["narrative"],
            "contextTags": _parse_tags(row["contextTags"]),
            "hypotheticalQueries": _parse_list(row["hypotheticalQueries"]),
            "migrationRef": row["Ref"],
            "migrationSource": source_name,
        }
        memories.append(memory)

    ideas: list[dict[str, Any]] = []
    for row in _parse_markdown_table(_extract_section(markdown, "Ideas")):
        idea: dict[str, Any] = {
            "docType": "idea",
            "narrative": row["narrative"],
            "rawText": row["narrative"],
            "contextTags": _parse_tags(row["contextTags"]),
            "migrationRef": row["Ref"],
            "migrationSource": source_name,
        }
        ideas.append(idea)

    return user_settings, tasks + goals + memories + ideas


async def ensure_user_settings(client: Client, document: dict[str, Any]) -> None:
    existing = await client.call_tool("query", {"docType": "userSettings", "limit": 5})
    existing_docs = existing.data.get("results", [])
    if not existing_docs:
        created = await client.call_tool("write", {"document": document})
        print(f"created userSettings: {created.data['id']}")
        return

    current = existing_docs[0]
    if current.get("tagTaxonomy") == document.get("tagTaxonomy"):
        print(f"skipped userSettings: {current['id']}")
        return

    updated = await client.call_tool(
        "update",
        {
            "id": current["id"],
            "updates": {
                "tagTaxonomy": document["tagTaxonomy"],
                "migrationSource": document["migrationSource"],
            },
        },
    )
    print(f"updated userSettings: {updated.data['id']}")


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
    parser.add_argument("--source", default="openbrain-migration-items.md")
    args = parser.parse_args()

    state = load_state(args.environment)
    url = args.url or f"https://{state['containerAppFqdn']}/mcp"
    token = args.token or state["openBrainApiToken"]
    source_path = Path(args.source)
    user_settings, documents = load_documents_from_markdown(source_path)

    client = Client(url, auth=token)
    async with client:
        await ensure_user_settings(client, user_settings)
        for document in documents:
            await ensure_document(client, document)


if __name__ == "__main__":
    anyio.run(main)
