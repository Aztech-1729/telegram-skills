#!/usr/bin/env python3
"""Plan AI maintenance, acknowledge reviewed evidence and gate exact-commit merges.

This helper does not invoke a model or treat an observation as an approval.
Run it from trusted main; the separate Codex schedule follows the review runbook.
"""
import argparse
import base64
import binascii
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

from automation_github import api, REPO, ROOT
import check_upstream as upstream

PREFIX = f"repos/{REPO}"
MARKER = "<!-- telegram-skills-agent-maintenance -->"
AGENT_BRANCH = "automation/agent-maintenance-"
ACTION_APP = 15368
SHA = re.compile(r"[a-f0-9]{40}")
DIGEST = re.compile(r"[a-f0-9]{64}")
PLUGIN_MANIFESTS = {".codex-plugin/plugin.json", ".claude-plugin/plugin.json"}
PLUGIN_VERSION = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
MAX_MANIFEST_BYTES = 64 * 1024
WORKFLOWS = {"validate.yml": 8 * 24, "upstream-refresh.yml": 48,
             "dependabot-automerge.yml": None, "automation-alerts.yml": None}


def now():
    return datetime.now(timezone.utc)


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamps must include a timezone")
    return result.astimezone(timezone.utc)


def paginated(path):
    rows = []
    for page in range(1, 6):
        result = api(f"{path}{'&' if '?' in path else '?'}per_page=100&page={page}")
        rows.extend(result)
        if len(result) < 100:
            return rows
    raise ValueError("Result exceeds the bounded maintenance batch")


def owned_pr(pr):
    if (pr["state"] != "open" or pr.get("draft") or
            pr["base"]["ref"] != "main" or pr["base"]["repo"]["full_name"] != REPO or
            not pr["head"].get("repo") or pr["head"]["repo"]["full_name"] != REPO):
        return False
    author, branch = pr["user"]["login"], pr["head"]["ref"]
    return (author in {"dependabot[bot]", "github-actions[bot]"} and
            (author == "dependabot[bot]" or branch == "automation/upstream-refresh")) or (
            author == REPO.split("/")[0] and branch.startswith(AGENT_BRANCH) and
            MARKER in (pr.get("body") or ""))


def plan(root=ROOT, current_time=None):
    current_time = current_time or now()
    state = json.loads((root / "automation/upstream-state.json").read_text(encoding="utf-8"))
    repository = api(PREFIX)
    if repository["full_name"] != REPO or repository["default_branch"] != "main":
        raise ValueError("Unexpected repository identity/default branch")
    main_sha = api(PREFIX + "/git/ref/heads/main")["object"]["sha"]
    sources = []
    for url, entry in sorted(state["sources"].items()):
        if entry.get("pending_change_since") or entry.get("last_failure"):
            sources.append({"url": url, "sha256": entry.get("sha256"),
                            "skills": entry["skills"], "pending_since": entry.get("pending_change_since"),
                            "failure_kind": entry.get("last_failure", {}).get("failure_kind"),
                            "last_success": entry.get("last_checked_at")})
    prs = [{"number": p["number"], "author": p["user"]["login"],
            "branch": p["head"]["ref"], "head_sha": p["head"]["sha"],
            "base_sha": p["base"]["sha"], "url": p["html_url"],
            "auto_merge": bool(p.get("auto_merge"))}
           for p in paginated(PREFIX + "/pulls?state=open&base=main") if owned_pr(p)]
    workflows = []
    for filename, maximum_age in WORKFLOWS.items():
        workflow = api(PREFIX + f"/actions/workflows/{filename}")
        item = {"file": filename, "state": workflow["state"],
                "needs_attention": workflow["state"] != "active"}
        if maximum_age is not None:
            runs = api(PREFIX + f"/actions/workflows/{filename}/runs?branch=main&per_page=20")["workflow_runs"]
            completed = next((r for r in runs if r["status"] == "completed" and
                              r["head_repository"]["full_name"] == REPO), None)
            item.update({"last_completed_at": completed["updated_at"] if completed else None,
                         "conclusion": completed["conclusion"] if completed else None,
                         "run_url": completed["html_url"] if completed else None})
            stale = not completed or current_time - timestamp(completed["updated_at"]) > timedelta(hours=maximum_age)
            item["stale"] = stale
            item["needs_attention"] |= stale or bool(completed and completed["conclusion"] != "success")
        workflows.append(item)
    observation_stale = current_time - timestamp(state["last_run_at"]) > timedelta(hours=48)
    return {"schema_version": 1, "repository": REPO, "main_sha": main_sha,
            "planned_at": current_time.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "observations_stale": observation_stale, "sources": sources, "pull_requests": prs,
            "workflows": workflows,
            "needs_attention": observation_stale or bool(sources or prs) or any(w["needs_attention"] for w in workflows)}


def acknowledge(reviews, root=ROOT, fetcher=None, current_time=None):
    """Refetch every requested hash before any write; unrelated evidence is retained."""
    if (reviews.get("schema_version") != 1 or not isinstance(reviews.get("reviewer"), str) or
            not reviews["reviewer"].strip() or not isinstance(reviews.get("sources"), list) or
            not 1 <= len(reviews["sources"]) <= 25):
        raise ValueError("Expected a named review of 1..25 source hashes")
    state_path = root / "automation/upstream-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    config = json.loads((root / "automation/sources.json").read_text(encoding="utf-8"))
    sources = {s["url"]: s for s in upstream.load_sources(root, config)}
    fetcher = fetcher or (lambda source: upstream.fetch_source(source, config, 15, 24 * 1024 * 1024))
    checked_at = (current_time or now()).isoformat(timespec="seconds").replace("+00:00", "Z")
    updated, seen = deepcopy(state), set()
    for review in reviews["sources"]:
        url, digest = review["url"], review["sha256"]
        notes = review.get("notes")
        if (url in seen or url not in sources or url not in state["sources"] or
                not isinstance(digest, str) or not DIGEST.fullmatch(digest) or
                review.get("decision") not in {"updated", "cosmetic", "not-applicable"} or
                not isinstance(notes, str) or not 1 <= len(notes.strip()) <= 4000):
            raise ValueError("Invalid, duplicate or untracked source review")
        seen.add(url)
        entry = state["sources"][url]
        if entry.get("last_failure") or entry.get("sha256") != digest:
            raise ValueError("Source is unavailable or no longer has the reviewed hash")
        outcome = fetcher(sources[url])
        if not outcome["ok"] or outcome["sha256"] != digest:
            raise ValueError("Source changed or became unavailable after review; refresh and review again")
        target = updated["sources"][url]
        target.update({"reviewed_sha256": digest, "editorial_reviewed_at": checked_at,
                       "review_method": "agent-content-review",
                       "review_record": {"reviewer": reviews["reviewer"],
                                         "decision": review["decision"], "notes": notes.strip()}})
        target.pop("pending_change_since", None)
    # Acknowledgement is an editorial change; it does not pretend the whole
    # source catalogue was fetched at this time or advance source-ledger dates.
    rows = [{"url": url, "ok": not bool(e.get("last_failure")),
             "failure_kind": e.get("last_failure", {}).get("failure_kind"),
             "transient": e.get("last_failure", {}).get("transient", False)}
            for url, e in updated["sources"].items()]
    successful = [e for e in updated["sources"].values() if not e.get("last_failure")]
    baseline = sum(e.get("first_observed_at") == updated["last_run_at"] for e in successful)
    changed = sum(e.get("last_changed_at") == updated["last_run_at"] and
                  e.get("first_observed_at") != updated["last_run_at"] for e in successful)
    counts = {"total": len(rows), "unchanged": len(successful) - baseline - changed,
              "changed": changed, "baseline": baseline, "unavailable": sum(not r["ok"] for r in rows)}
    report = {"checked_at": updated["last_run_at"], "counts": counts, "sources": rows}
    upstream.atomic_write(state_path, json.dumps(updated, indent=2, ensure_ascii=False) + "\n")
    upstream.atomic_write(root / "docs/UPSTREAM_STATUS.md", upstream.markdown_report(report, updated))
    return {"acknowledged": len(seen), "reviewed_at": checked_at}


def snapshot(number, expected_head, expected_base):
    if not SHA.fullmatch(expected_head) or not SHA.fullmatch(expected_base):
        raise ValueError("Expected immutable Git commit identifiers")
    pr = api(PREFIX + f"/pulls/{number}")
    main_sha = api(PREFIX + "/git/ref/heads/main")["object"]["sha"]
    if (not owned_pr(pr) or pr["head"]["sha"] != expected_head or
            pr["base"]["sha"] != expected_base or main_sha != expected_base):
        raise ValueError("PR identity, head or base changed; update and review again")
    return pr


def files_digest(files):
    records = sorted(({k: f.get(k) for k in ("filename", "previous_filename", "status", "sha")}
                      for f in files), key=lambda f: f["filename"])
    return hashlib.sha256(json.dumps(records, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def review_template(number, expected_head, expected_base):
    snapshot(number, expected_head, expected_base)
    files = paginated(PREFIX + f"/pulls/{number}/files")
    return {"schema_version": 1, "repository": REPO, "pull_request": number,
            "head_sha": expected_head, "base_sha": expected_base,
            "files_sha256": files_digest(files), "reviewer": "", "reviewed_at": None,
            "approved": False, "findings": [],
            "instruction": "An independent reviewer must inspect the complete diff and official evidence before filling approval."}


def allowed_file(name, skills):
    path = PurePosixPath(name)
    if ("\\" in name or path.is_absolute() or any(p in {".", "..", ".git", ".github"} for p in name.split("/")) or
            any(p.startswith(".env") and p != ".env.example" for p in path.parts)):
        return False
    if name in {"README.md", "requirements-dev.txt", "package.json", "package-lock.json",
                "automation/upstream-state.json"}:
        return True
    if path.parts[0] in skills:
        return True
    if path.parts[0] == "docs":
        return name not in {"docs/AUTOMATION.md", "docs/AGENT_MAINTENANCE.md"} and path.suffix == ".md"
    # Root tests exercise maintenance and live-credential boundaries. Behavior
    # tests beside an affected skill's examples remain in the skill allowlist.
    return False


def unique_manifest_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate key in plugin manifest")
        result[key] = value
    return result


def invalid_manifest_constant(value):
    raise ValueError("Non-JSON constant in plugin manifest")


def immutable_manifest(entry):
    """Decode a bounded Git blob, verifying that its bytes match the tree SHA."""
    if (entry.get("type") != "blob" or entry.get("mode") != "100644" or
            not isinstance(entry.get("sha"), str) or not SHA.fullmatch(entry["sha"])):
        raise ValueError("Plugin manifest must be an existing regular Git blob")
    blob = api(PREFIX + "/git/blobs/" + entry["sha"])
    size, content = blob.get("size"), blob.get("content")
    if (blob.get("sha") != entry["sha"] or blob.get("encoding") != "base64" or
            type(size) is not int or not 0 < size <= MAX_MANIFEST_BYTES or
            not isinstance(content, str) or len(content) > MAX_MANIFEST_BYTES * 2):
        raise ValueError("Invalid or oversized plugin manifest blob")
    try:
        raw = base64.b64decode(content.replace("\n", "").replace("\r", ""), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Invalid base64 plugin manifest blob") from exc
    digest = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
    if len(raw) != size or digest != entry["sha"]:
        raise ValueError("Plugin manifest bytes do not match their immutable Git blob")
    try:
        manifest = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_manifest_object,
                              parse_constant=invalid_manifest_constant)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ValueError("Malformed plugin manifest JSON") from exc
    if not isinstance(manifest, dict):
        raise ValueError("Plugin manifest must be a JSON object")
    return manifest


def plugin_release(files, skills, expected_base, head_tree):
    """Allow only a paired patch release accompanying actual skill changes."""
    changed = {f["filename"]: f for f in files if f["filename"] in PLUGIN_MANIFESTS}
    candidates = [f for f in files if PurePosixPath(f["filename"]).parts[0] in skills and
                  not f["filename"].endswith("/references/upstream-status.md")]
    if not changed and not candidates:
        return
    if changed and (set(changed) != PLUGIN_MANIFESTS or
                    any(f["status"] != "modified" for f in changed.values())):
        raise ValueError("Both existing native plugin manifests must change together")
    base_tree = api(PREFIX + f"/git/trees/{expected_base}?recursive=1")
    if base_tree.get("truncated") or head_tree.get("truncated"):
        raise ValueError("Complete immutable trees are required for plugin releases")
    trees = [{e["path"]: e for e in tree["tree"]} for tree in (base_tree, head_tree)]
    if any(not isinstance(f.get("sha"), str) or not SHA.fullmatch(f["sha"]) or
           trees[1].get(f["filename"], {}).get("sha") != f["sha"] for f in candidates):
        raise ValueError("Skill content file digest is not from the reviewed head")
    content_changed = any(
        trees[0].get(f["filename"], {}).get("sha") != f["sha"]
        for f in candidates)
    if not changed:
        if content_changed:
            raise ValueError("Actual skill content changes require a paired native plugin patch release")
        return
    if not content_changed:
        raise ValueError("A native plugin release must accompany actual skill content changes")
    versions = [set(), set()]
    for name in sorted(PLUGIN_MANIFESTS):
        entries = [tree.get(name, {}) for tree in trees]
        if changed[name]["sha"] != entries[1].get("sha"):
            raise ValueError("Plugin manifest file digest is not from the reviewed head")
        manifests = [immutable_manifest(entry) for entry in entries]
        for index, manifest in enumerate(manifests):
            version = manifest.get("version")
            if not isinstance(version, str) or len(version) > 64 or not PLUGIN_VERSION.fullmatch(version):
                raise ValueError("Plugin versions must be exact numeric major.minor.patch strings")
            versions[index].add(tuple(int(part) for part in version.split(".")))
        bodies = [{key: value for key, value in manifest.items() if key != "version"}
                  for manifest in manifests]
        canonical = [json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                                allow_nan=False) for body in bodies]
        if canonical[0] != canonical[1]:
            raise ValueError("Native plugin release may change only the version field")
    if len(versions[0]) != 1 or len(versions[1]) != 1:
        raise ValueError("Native plugin manifests must have equal base and release versions")
    before, after = next(iter(versions[0])), next(iter(versions[1]))
    if after != (before[0], before[1], before[2] + 1):
        raise ValueError("Native plugin release must increment the current patch version exactly once")


def merge(number, expected_head, expected_base, review, root=ROOT, current_time=None):
    current_time = current_time or now()
    pr = snapshot(number, expected_head, expected_base)
    if pr.get("auto_merge"):
        raise ValueError("Disable retained auto-merge before independent semantic review")
    protection = api(PREFIX + "/branches/main/protection")
    checks_policy = protection.get("required_status_checks", {})
    if (not protection.get("enforce_admins", {}).get("enabled") or
            checks_policy.get("strict") is not True or not any(
            c.get("context") == "validation" and c.get("app_id") == ACTION_APP
            for c in checks_policy.get("checks", []))):
        raise ValueError("Strict GitHub Actions validation protection, including administrators, is required")
    files = paginated(PREFIX + f"/pulls/{number}/files")
    skills = {p.parent.name for p in root.glob("telegram-bot-*/SKILL.md")}
    if not files or any(f["status"] not in {"added", "modified"} or
                        not (allowed_file(f["filename"], skills) or f["filename"] in PLUGIN_MANIFESTS)
                        for f in files):
        raise ValueError("Change touches foundation/policy files or deletes/renames; automatic merge refused")
    tree = api(PREFIX + f"/git/trees/{expected_head}?recursive=1")
    modes = {e["path"]: (e["type"], e["mode"]) for e in tree["tree"]}
    if tree.get("truncated") or any(modes.get(f["filename"]) != ("blob", "100644") for f in files):
        raise ValueError("Incomplete tree, symlink, submodule or non-regular changed file")
    plugin_release(files, skills, expected_base, tree)
    if (review.get("schema_version") != 1 or review.get("repository") != REPO or
            review.get("pull_request") != number or review.get("head_sha") != expected_head or
            review.get("base_sha") != expected_base or review.get("files_sha256") != files_digest(files) or
            review.get("approved") is not True or review.get("findings") != [] or
            not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip()):
        raise ValueError("Missing/rejected/stale independent review for this exact change")
    reviewed_at = timestamp(review["reviewed_at"])
    if not timedelta(minutes=-5) <= current_time - reviewed_at <= timedelta(hours=48):
        raise ValueError("Review has expired or is dated in the future")
    runs = api(PREFIX + f"/actions/workflows/validate.yml/runs?event=pull_request&head_sha={expected_head}&per_page=20")["workflow_runs"]
    matching = [r for r in runs if r["head_sha"] == expected_head and r["event"] == "pull_request" and
                r["path"] == ".github/workflows/validate.yml" and r["head_branch"] == pr["head"]["ref"] and
                r["head_repository"]["full_name"] == REPO and
                any(p["number"] == number for p in r["pull_requests"])]
    latest = max(matching, key=lambda r: (r["id"], r.get("run_attempt", 1)), default=None)
    if not latest or latest["status"] != "completed" or latest["conclusion"] != "success":
        raise ValueError("Exact-head native PR validation has not passed")
    checks = api(PREFIX + f"/commits/{expected_head}/check-runs?check_name=validation&filter=latest&per_page=100")["check_runs"]
    if not any(c["name"] == "validation" and c["app"]["id"] == ACTION_APP and
               c["head_sha"] == expected_head and c["status"] == "completed" and c["conclusion"] == "success" and
               c["details_url"].startswith(f"https://github.com/{REPO}/actions/runs/{latest['id']}/job/")
               for c in checks):
        raise ValueError("Required check is missing or is not from the validated native run")
    # Re-read identity immediately before merge. GitHub's strict required gate
    # enforces base freshness at merge time, including a race after this read.
    pr = snapshot(number, expected_head, expected_base)
    if pr.get("auto_merge") or not pr.get("mergeable") or pr["mergeable_state"] != "clean":
        raise ValueError("PR is no longer immediately mergeable with current main")
    result = subprocess.run(["gh", "pr", "merge", str(number), "--repo", REPO,
                             "--squash", "--match-head-commit", expected_head],
                            text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError("Protected exact-head merge failed; no bypass or delayed auto-merge requested")
    merged = api(PREFIX + f"/pulls/{number}")
    if not merged.get("merged") or merged["head"]["sha"] != expected_head:
        raise RuntimeError("Merge was not confirmed for the reviewed commit")
    return {"merged": True, "pull_request": number, "head_sha": expected_head,
            "merge_commit_sha": merged["merge_commit_sha"], "url": merged["html_url"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    planning = commands.add_parser("plan")
    planning.add_argument("--output", type=Path)
    acknowledgement = commands.add_parser("acknowledge")
    acknowledgement.add_argument("--reviews", type=Path, required=True)
    for name in ("review-template", "merge"):
        command = commands.add_parser(name)
        command.add_argument("--pr", type=int, required=True)
        command.add_argument("--expected-head", required=True)
        command.add_argument("--expected-base", required=True)
        command.add_argument("--output" if name == "review-template" else "--review", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            result = plan()
        elif args.command == "acknowledge":
            result = acknowledge(json.loads(args.reviews.read_text(encoding="utf-8")))
        elif args.command == "review-template":
            result = review_template(args.pr, args.expected_head, args.expected_base)
        else:
            result = merge(args.pr, args.expected_head, args.expected_base,
                           json.loads(args.review.read_text(encoding="utf-8")))
        payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        if getattr(args, "output", None):
            upstream.atomic_write(args.output, payload)
        else:
            print(payload, end="")
        return 0
    except (KeyError, TypeError, ValueError, OSError, RuntimeError) as exc:
        # Controlled messages only; never print subprocess output or credentials.
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
