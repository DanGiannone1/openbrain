#!/usr/bin/env python3
"""
UserPromptSubmit hook: re-inject CLAUDE.md on every prompt.
"""

import json
import os
import sys


def find_claude_md():
    current = os.getcwd()
    while True:
        candidate = os.path.join(current, "CLAUDE.md")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def main():
    path = find_claude_md()
    if not path:
        sys.exit(0)

    try:
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
    except Exception:
        sys.exit(0)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": (
                "=== CLAUDE.md (re-injected by hook) ===\n"
                f"{content}\n"
                "=== END CLAUDE.md ==="
            ),
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
