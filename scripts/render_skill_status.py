#!/usr/bin/env python3
"""Render bounded source observations beside each skill; never rewrite its instructions."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def safe_version(value):
    # Upstream strings cannot become Markdown instructions, HTML or mentions.
    return value if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9.+_-]{1,80}", value) else "unrecognized version"


def render(root=ROOT):
    state = json.loads((root / "automation/upstream-state.json").read_text(encoding="utf-8"))
    for skill in sorted(root.glob("telegram-bot-*/SKILL.md")):
        name = skill.parent.name
        entries = [(url, item) for url, item in state["sources"].items() if name in item["skills"]]
        failed = [(url, item) for url, item in entries if item.get("last_failure")]
        pending = [(url, item) for url, item in entries if item.get("pending_change_since")]
        lines = ["# Upstream observations", "", f"Generated from the source check at **{state['last_run_at']}**.", "",
                 f"{len(entries)} tracked sources; {len(failed)} unavailable; {len(pending)} changed sources await content review.", "",
                 "Read [the source register](sources.md) for the editorial review and framework baseline. "
                 "These machine observations do not certify compatibility or advance that review date. "
                 "Compare your installed dependency with the observed versions before using new APIs.", "",
                 "## Release observations", "", "| Official feed | Observed versions |", "| --- | --- |"]
        feeds = [(url, item) for url, item in entries if item.get("release_versions")]
        for url, item in feeds:
            versions = ", ".join(safe_version(v) for v in item["release_versions"][:5])
            channel = " (includes release candidates)" if item["kind"] == "github-prerelease" else ""
            lines.append(f"| [{url}]({url}){channel} | {versions} |")
        if not feeds:
            lines.append("| This skill uses documentation sources rather than a dedicated release feed | — |")
        lines += ["", "## Changes and availability", ""]
        for url, item in pending:
            lines.append(f"- Content changed: [{url}]({url}); first detected {item['pending_change_since']}.")
        for url, item in failed:
            lines.append(f"- Unavailable: [{url}]({url}); {item['last_failure']['failure_kind']}. Last successful evidence is retained.")
        if not failed and not pending:
            lines.append("All tracked sources were available and no unresolved change was detected against the stored observations.")
        lines += ["", "See the [repository source status](https://github.com/Aztech-1729/telegram-skills/blob/main/docs/UPSTREAM_STATUS.md) and "
                  "[automation policy](https://github.com/Aztech-1729/telegram-skills/blob/main/docs/AUTOMATION.md) for coverage and review steps.", ""]
        (skill.parent / "references/upstream-status.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    render()
