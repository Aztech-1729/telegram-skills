#!/usr/bin/env python3
"""Observe authoritative upstream docs/releases; never rewrite skills from fetched text.

Standard library only. Run from anywhere; paths default to this repository.
The network response is untrusted data and is never executed or sent to a model.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
from http.client import IncompleteRead, RemoteDisconnected
import json
from pathlib import Path
import re
import socket
import ssl
import sys
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
URL_RE = re.compile(r"https://[^\s<>\)\]\"`]+")
USER_AGENT = "telegram-skills-source-monitor/1.0 (+https://github.com/Aztech-1729/telegram-skills)"
TRANSIENT_CODES = {408, 425, 429, 500, 502, 503, 504}


class CheckError(Exception):
    def __init__(self, kind: str, message: str, transient: bool = False):
        super().__init__(message)
        self.kind, self.transient = kind, transient


def canonical_url(url: str) -> str:
    """Deduplicate fragments; never drop semantic query parameters."""
    p = urlsplit(url.strip())
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        raise CheckError("untrusted_url", "Only HTTPS URLs without credentials are allowed")
    try:
        if p.port not in (None, 443):
            raise CheckError("untrusted_url", "Only the default HTTPS port is allowed")
    except ValueError as exc:
        raise CheckError("untrusted_url", "Invalid port") from exc
    if any(ord(c) < 33 for c in url) or "\\" in url:
        raise CheckError("untrusted_url", "Invalid URL characters")
    decoded = p.path
    for _ in range(4):
        decoded = unquote(decoded)
        if any(part in (".", "..") for part in decoded.split("/")) or "\\" in decoded:
            raise CheckError("untrusted_url", "Path traversal is not allowed")
    return urlunsplit(("https", p.hostname.lower(), p.path or "/", p.query, ""))


def validate_url(url: str, config: dict) -> str:
    url = canonical_url(url)
    p = urlsplit(url)
    origin = "https://" + p.netloc
    allowed = config["allowed_origins"].get(origin)
    if allowed is None or not any(prefix == "/" or p.path == prefix.rstrip("/") or
                                   p.path.startswith(prefix.rstrip("/") + "/") for prefix in allowed):
        raise CheckError("untrusted_url", "Origin/path is outside the configured source allowlist")
    return url


def fetch_url_for(url: str) -> str:
    """Use stable raw content for GitHub file views, avoiding dynamic UI noise."""
    p = urlsplit(url)
    parts = p.path.strip("/").split("/")
    if p.hostname == "github.com" and len(parts) >= 5 and parts[2] == "blob":
        return "https://raw.githubusercontent.com/" + "/".join(parts[:2] + parts[3:])
    return url


def load_sources(root: Path, config: dict) -> list[dict]:
    records: dict[str, dict] = {}
    ledgers = sorted(root.glob("telegram-bot-*/references/sources.md"))
    if not ledgers:
        raise ValueError("No skill source ledgers found")
    for path in ledgers:
        skill = path.relative_to(root).parts[0]
        ledger = path.read_text(encoding="utf-8")
        date_match = re.search(r"\b20\d\d-\d\d-\d\d\b", ledger[:1000])
        for raw in URL_RE.findall(ledger):
            url = validate_url(raw.rstrip(".,;"), config)
            record = records.setdefault(url, {"url": url, "kind": "document", "skills": [], "skill_ledger_review_dates": {}})
            if skill not in record["skills"]:
                record["skills"].append(skill)
            if date_match:
                record["skill_ledger_review_dates"][skill] = date_match.group()
    for item in config.get("additional_sources", []):
        item = dict(item)
        url = validate_url(item["url"], config)
        existing_skills = records.get(url, {}).get("skills", [])
        item["skill_ledger_review_dates"] = records.get(url, {}).get("skill_ledger_review_dates", {})
        item["url"] = url
        item["skills"] = sorted(set(existing_skills + item.get("skills", [])))
        records[url] = item
    for record in records.values():
        record["fetch_url"] = validate_url(config.get("fetch_overrides", {}).get(record["url"], fetch_url_for(record["url"])), config)
    return sorted(records.values(), key=lambda x: x["url"])


class ContentParser(HTMLParser):
    """Prefer article/main content and remove repeated navigation/UI chrome."""
    SKIP_TAGS = {"script", "style", "nav", "header", "footer", "noscript", "svg", "form"}
    SKIP_NAMES = {"sidebar", "toc", "table-of-contents", "breadcrumb", "breadcrumbs", "pagination",
                  "edit-page", "theme-toggle", "search", "feedback", "announcement"}
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, bool, int]] = []
        self.parts: dict[int, list[str]] = {0: [], 1: [], 2: [], 3: []}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        names = set(re.split(r"\s+", (attrs.get("class") or "") + " " + (attrs.get("id") or "")))
        inherited_skip = self.stack[-1][1] if self.stack else False
        inherited_rank = self.stack[-1][2] if self.stack else 0
        skip = inherited_skip or tag in self.SKIP_TAGS or bool(names & self.SKIP_NAMES) or attrs.get("aria-hidden") == "true"
        rank = max(inherited_rank, 3 if tag == "article" or "markdown-body" in names else
                   2 if tag == "main" or attrs.get("role") == "main" or "dev_page_content" in names else 0)
        if tag not in self.VOID:
            self.stack.append((tag, skip, rank))

    def handle_startendtag(self, tag, attrs):
        if tag not in self.VOID:
            self.handle_starttag(tag, attrs)
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        skip = self.stack[-1][1] if self.stack else False
        rank = self.stack[-1][2] if self.stack else 0
        if not skip and data.strip():
            self.parts[rank].append(data)

    def content(self):
        for rank in (3, 2, 1, 0):
            if self.parts[rank]:
                return " ".join(self.parts[rank])
        return ""


def release_summary(value, kind: str):
    """Hash semantic release identity/body; ignore counters, URLs, downloads and timestamps."""
    def identity(obj, *keys):
        if not isinstance(obj, dict) or any(not isinstance(obj.get(k), str) or not obj[k].strip() for k in keys):
            raise CheckError("invalid_payload", "Release identity is missing or malformed")
    if kind in ("github-release", "github-prerelease"):
        if not isinstance(value, list):
            value = [value]
        for item in value:
            identity(item, "tag_name")
        releases = [x for x in value if not x.get("draft") and (kind == "github-prerelease" or not x.get("prerelease"))]
        if not releases:
            raise CheckError("invalid_payload", "No release in the configured channel")
        return [{k: x.get(k) for k in ("tag_name", "name", "body", "prerelease")} for x in releases[:5]]
    if kind == "pypi-release":
        info = value.get("info") if isinstance(value, dict) else None
        identity(info, "name", "version")
        return {k: info.get(k) for k in ("name", "version", "requires_python", "requires_dist")}
    if kind == "npm-release":
        identity(value, "name", "version")
        return {k: value.get(k) for k in ("name", "version", "engines", "dependencies", "peerDependencies")}
    if kind == "nuget-versions":
        if not isinstance(value, dict) or not isinstance(value.get("versions"), list) or not value["versions"] or not all(isinstance(v, str) and v for v in value["versions"]):
            raise CheckError("invalid_payload", "Invalid NuGet versions")
        stable = [v for v in value["versions"] if "-" not in v][-10:]
        if not stable:
            raise CheckError("invalid_payload", "Missing stable NuGet release")
        return stable
    if kind == "packagist-release":
        if not isinstance(value, dict) or not isinstance(value.get("packages"), dict) or not value["packages"]:
            raise CheckError("invalid_payload", "Invalid Packagist packages")
        versions = next(iter(value["packages"].values()))
        if not isinstance(versions, list) or not versions:
            raise CheckError("invalid_payload", "Missing Packagist versions")
        for item in versions:
            identity(item, "version")
        stable = [x for x in versions if not re.search(r"dev|alpha|beta|rc", x["version"], re.I)]
        if not stable:
            raise CheckError("invalid_payload", "Missing stable Packagist release")
        return [{k: x.get(k) for k in ("name", "version", "require")} for x in stable[:5]]
    if kind == "crates-release":
        identity(value.get("crate") if isinstance(value, dict) else None, "id", "max_stable_version")
        return {k: value["crate"].get(k) for k in ("id", "max_stable_version", "newest_version")}
    return value


def release_versions(body: bytes, kind: str) -> list[str]:
    if kind == "document":
        return []
    value = release_summary(json.loads(body.decode("utf-8")), kind)
    if kind in ("github-release", "github-prerelease"):
        return [x["tag_name"] for x in value]
    if kind in ("pypi-release", "npm-release"):
        return [value["version"]]
    if kind == "nuget-versions":
        return list(reversed(value))
    if kind == "packagist-release":
        return [x["version"] for x in value]
    if kind == "crates-release":
        return [value["max_stable_version"]] if value.get("max_stable_version") else []
    return []


def normalized_content(body: bytes, content_type: str, kind="document") -> str:
    text = body.decode("utf-8", errors="replace")
    if "json" in content_type or kind.endswith("release") or kind == "nuget-versions":
        try:
            return json.dumps(release_summary(json.loads(text), kind), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        except (ValueError, KeyError, TypeError, StopIteration) as exc:
            raise CheckError("invalid_payload", "Unexpected JSON source shape") from exc
    if "html" in content_type or re.search(r"<(?:html|!doctype html)\b", text[:500], re.I):
        parser = ContentParser()
        parser.feed(text)
        text = parser.content()
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) < 20:
        raise CheckError("empty_content", "No meaningful content was extracted")
    if any(marker in text[:1500].lower() for marker in ("just a moment...", "verify you are human", "enable javascript and cookies to continue")):
        raise CheckError("challenge_page", "Upstream returned an anti-bot challenge", True)
    return text


class GuardedRedirectHandler(HTTPRedirectHandler):
    def __init__(self, config):
        self.config = config

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(urljoin(req.full_url, newurl), self.config)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def classify_exception(exc: Exception) -> CheckError:
    if isinstance(exc, CheckError):
        return exc
    if isinstance(exc, HTTPError):
        transient = exc.code in TRANSIENT_CODES or (exc.code == 403 and exc.headers.get("X-RateLimit-Remaining") == "0")
        return CheckError("http_" + str(exc.code), "HTTP " + str(exc.code), transient)
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return CheckError("timeout", "Request exceeded its time limit", True)
    if isinstance(exc, (IncompleteRead, RemoteDisconnected, ConnectionError)):
        return CheckError("network_error", "Upstream response was interrupted", True)
    if isinstance(exc, ssl.SSLError):
        return CheckError("tls_error", "TLS validation failed")
    if isinstance(exc, URLError):
        if isinstance(exc.reason, ssl.SSLError):
            return CheckError("tls_error", "TLS validation failed")
        return CheckError("network_error", "Network request failed", True)
    return CheckError("unexpected_error", type(exc).__name__)


def fetch_source(source: dict, config: dict, timeout: float, max_bytes: int, attempts: int = 2) -> dict:
    started = time.monotonic()
    for attempt in range(attempts):
        try:
            url = validate_url(source["fetch_url"], config)
            request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json, text/html, text/plain;q=0.9"})
            opener = build_opener(GuardedRedirectHandler(config))
            with opener.open(request, timeout=timeout) as response:
                validate_url(response.geturl(), config)
                if int(response.headers.get("Content-Length", 0)) > max_bytes:
                    raise CheckError("oversize", "Response exceeds the configured byte limit")
                chunks, total = [], 0
                deadline = time.monotonic() + timeout
                while total <= max_bytes:
                    if time.monotonic() >= deadline:
                        raise CheckError("timeout", "Response exceeded its read deadline", True)
                    chunk = response.read1(min(65536, max_bytes + 1 - total))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    total += len(chunk)
                body = b"".join(chunks)
                if len(body) > max_bytes:
                    raise CheckError("oversize", "Response exceeds the configured byte limit")
                normalized = normalized_content(body, response.headers.get("Content-Type", ""), source["kind"])
                return {"ok": True, "sha256": hashlib.sha256(normalized.encode()).hexdigest(),
                        "bytes": len(body), "normalized_characters": len(normalized),
                        "final_url": response.geturl(), "release_versions": release_versions(body, source["kind"]),
                        "seconds": round(time.monotonic() - started, 3)}
        except Exception as exc:
            failure = classify_exception(exc)
            if failure.transient and attempt + 1 < attempts:
                time.sleep(min(2 ** attempt, 4))
                continue
            return {"ok": False, "failure_kind": failure.kind, "message": str(failure),
                    "transient": failure.transient, "seconds": round(time.monotonic() - started, 3)}
    raise AssertionError("Unreachable")


def reconcile(source: dict, outcome: dict, previous: dict | None, checked_at: str) -> tuple[dict, dict]:
    entry = dict(previous or {})
    row = {"url": source["url"], "kind": source["kind"], "skills": source["skills"], **outcome}
    entry.update({"kind": source["kind"], "skills": source["skills"], "last_attempt_at": checked_at,
                  "skill_ledger_review_dates": source.get("skill_ledger_review_dates", {})})
    if not outcome["ok"]:
        row["status"] = "unavailable"
        entry["last_failure"] = {k: outcome[k] for k in ("failure_kind", "message", "transient")}
        return entry, row
    digest = outcome["sha256"]
    old_digest = entry.get("sha256")
    row["status"] = "baseline" if not old_digest else "unchanged" if old_digest == digest else "changed"
    entry.update({"sha256": digest, "last_checked_at": checked_at, "final_url": outcome["final_url"],
                  "release_versions": outcome.get("release_versions", [])})
    entry.pop("last_failure", None)
    if not old_digest:
        entry.update({"first_observed_at": checked_at, "baseline_sha256": digest, "reviewed_sha256": None,
                      "editorial_reviewed_at": None})
    elif old_digest != digest:
        entry["last_changed_at"] = checked_at
        entry.setdefault("pending_change_since", checked_at)
        row["previous_sha256"] = old_digest
    row["pending_review"] = bool(entry.get("pending_change_since"))
    return entry, row


def run_checks(sources, config, state, checked_at, fetcher, workers=6):
    host_locks = {urlsplit(s["fetch_url"]).hostname: threading.Semaphore(2) for s in sources}
    def check(source):
        with host_locks[urlsplit(source["fetch_url"]).hostname]:
            return source, fetcher(source)
    entries, rows = {}, []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for source, outcome in pool.map(check, sources):
            entry, row = reconcile(source, outcome, state.get("sources", {}).get(source["url"]), checked_at)
            entries[source["url"]] = entry
            rows.append(row)
    counts = {key: sum(r["status"] == key for r in rows) for key in ("baseline", "changed", "unchanged", "unavailable")}
    counts["total"] = len(rows)
    counts["pending_review"] = sum(bool(e.get("pending_change_since")) for e in entries.values())
    counts["transient_failures"] = sum(r.get("transient", False) for r in rows)
    report = {"schema_version": 1, "checked_at": checked_at, "counts": counts, "sources": rows,
              "changed_sources": [r["url"] for r in rows if r["status"] == "changed"],
              "failed_sources": [r["url"] for r in rows if r["status"] == "unavailable"],
              "pending_review_sources": [url for url, entry in entries.items() if entry.get("pending_change_since")],
              "policy": "Observed hashes are machine evidence, not editorial approval. Skill instructions are never modified."}
    new_state = {"schema_version": 1, "last_run_at": checked_at, "sources": entries}
    return new_state, report


def markdown_report(report: dict, state: dict) -> str:
    counts = report["counts"]
    lines = ["# Upstream source status", "", f"Last attempted check: **{report['checked_at']}**.", "",
             f"{counts['total']} sources: {counts['unchanged']} unchanged, {counts['changed']} changed this run, "
             f"{counts['baseline']} newly observed, {counts['unavailable']} unavailable.", "",
             "This generated report checks the official source ledgers and configured release feeds. "
             "A successful fetch establishes an observed content hash. It does **not** certify that a person or "
             "agent reviewed the content, that the guides support the new release, or that examples were tested against it.", "",
             "The original editorial audit is recorded separately in each skill's `references/sources.md`. "
             "Machine checks never advance those dates or change instructions. A pending change remains visible "
             "after subsequent unchanged checks until its state is explicitly reviewed in a content update.", "",
             "## Changes requiring content review", "",
             "| Official source | Affected skills | First detected |", "| --- | --- | --- |"]
    pending = [(url, entry) for url, entry in state["sources"].items() if entry.get("pending_change_since")]
    for url, entry in pending:
        skills = ", ".join(x.removeprefix("telegram-bot-") for x in entry["skills"]) or "shared infrastructure"
        lines.append(f"| [{url}]({url}) | {skills} | {entry['pending_change_since']} |")
    if not pending:
        lines.append("| No changes since the observed baselines | — | — |")
    lines += ["", "## Unavailable sources", "", "Failures keep the last successful hash and check date; they never become accepted content.", "",
              "| Source | Failure | Retry classification |", "| --- | --- | --- |"]
    failures = [r for r in report["sources"] if not r["ok"]]
    for row in failures:
        lines.append(f"| [{row['url']}]({row['url']}) | {row['failure_kind']} | {'transient' if row['transient'] else 'needs investigation'} |")
    if not failures:
        lines.append("| None | — | — |")
    lines += ["", "## Observed release feeds", "", "Versions below are upstream observations, not upgraded or certified example dependencies.", "",
              "| Feed | Observed versions (gotgbot includes release candidates) | Last successful check |", "| --- | --- | --- |"]
    for url, entry in state["sources"].items():
        if entry.get("release_versions"):
            versions = [v if isinstance(v, str) and re.fullmatch(r"[A-Za-z0-9.+_-]{1,80}", v) else "unrecognized version" for v in entry['release_versions'][:5]]
            lines.append(f"| [{url}]({url}) | {', '.join(versions)} | {entry['last_checked_at']} |")
    lines += ["", "## Coverage and operation", "",
              "- Every HTTPS link in `telegram-bot-*/references/sources.md` is harvested and deduplicated without its fragment.",
              "- `automation/sources.json` adds current documentation and stable-release feeds; it also restricts destinations and redirects.",
              "- HTML navigation is discarded; JSON release feeds retain semantic release fields. Website layout changes may still require triage.",
              "- Requests have time and size limits, bounded retries and per-host concurrency. Private endpoints and credentials are not used.",
              "- Run `python scripts/check_upstream.py --write --report-json upstream-report.json` to refresh generated evidence.",
              "- Run with `--strict` to fail on any unavailable source. The default exits successfully for recorded upstream failures so evidence can be published.",
              "- `automation/upstream-state.json` preserves successful observation dates, hashes and unresolved changes. "
              "After updating and testing affected guides, explicitly set `reviewed_sha256` to the current hash, "
              "set `editorial_reviewed_at`, and remove `pending_change_since` for reviewed entries.", ""]
    return "\n".join(lines)


def atomic_write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(text, encoding="utf-8", newline="\n")
    temp.replace(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--report-json", type=Path)
    parser.add_argument("--write", action="store_true", help="Write generated state and Markdown, preserving failed-source baselines")
    parser.add_argument("--strict", action="store_true", help="Exit 1 when any source is unavailable")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--max-bytes", type=int, default=24 * 1024 * 1024)
    parser.add_argument("--limit", type=int, help="Read-only diagnostic subset; cannot be combined with --write")
    args = parser.parse_args(argv)
    if not 1 <= args.workers <= 16 or not 1 <= args.timeout <= 120 or not 1024 <= args.max_bytes <= 32 * 1024 * 1024:
        parser.error("workers must be 1..16, timeout 1..120, and max-bytes 1024..33554432")
    if args.limit is not None and (args.limit < 1 or args.write):
        parser.error("--limit must be positive and cannot be combined with --write")
    root = args.root.resolve()
    config_path = args.config or root / "automation/sources.json"
    state_path = args.state or root / "automation/upstream-state.json"
    report_path = args.report or root / "docs/UPSTREAM_STATUS.md"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {"sources": {}}
        if config.get("schema_version") != 1 or state.get("schema_version", 1) != 1:
            raise ValueError("Unsupported state/config schema")
        sources = load_sources(root, config)
        if args.limit:
            sources = sources[:args.limit]
        checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        new_state, report = run_checks(sources, config, state, checked_at,
            lambda source: fetch_source(source, config, args.timeout, args.max_bytes), args.workers)
        payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.report_json:
            atomic_write(args.report_json, payload)
        if args.write:
            atomic_write(state_path, json.dumps(new_state, indent=2, ensure_ascii=False) + "\n")
            atomic_write(report_path, markdown_report(report, new_state))
        print(payload, end="")
        return 1 if args.strict and report["counts"]["unavailable"] else 0
    except (ValueError, OSError, CheckError) as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
