#!/usr/bin/env python3
"""Publish generated evidence and deduplicated alerts using the job's GITHUB_TOKEN."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
REPO = "Aztech-1729/telegram-skills"
BRANCH = "automation/upstream-refresh"
COMMIT = "chore: refresh upstream observations [source-monitor]"


def api(path, method="GET", data=None, missing=False):
    command = ["gh", "api", path, "--method", method]
    if data is not None:
        command += ["--input", "-"]
    result = subprocess.run(command, input=json.dumps(data) if data is not None else None,
                            text=True, capture_output=True, check=False)
    if result.returncode:
        if missing and "HTTP 404" in result.stderr:
            return None
        # Never propagate headers, credentials or untrusted remote text into errors.
        raise RuntimeError(f"GitHub API {method} failed for {path.split('?')[0]}")
    return json.loads(result.stdout) if result.stdout.strip() else None


def generated_paths(root=ROOT):
    return ["automation/upstream-state.json", "docs/UPSTREAM_STATUS.md"] + [
        p.relative_to(root).as_posix() for p in sorted(root.glob("telegram-bot-*/references/upstream-status.md"))]


def protected():
    branch = api(f"repos/{REPO}/branches/main")
    checks = branch.get("protection", {}).get("required_status_checks", {})
    # Get-a-branch omits strict; its full endpoint needs Administration:read,
    # which the job token intentionally lacks. The owner verifies that setting
    # and GitHub enforces it. Reject an explicitly disabled value if returned.
    if not branch.get("protected") or checks.get("strict") is False or "validation" not in checks.get("contexts", []):
        raise RuntimeError("Required validation protection is not configured")


def issue(key, title, details):
    """Only edit our own marker issues, and only when substantive findings change."""
    marker = f"<!-- telegram-skills-automation:{key} -->"
    matches = []
    for page in range(1, 21):
        items = api(f"repos/{REPO}/issues?state=open&creator=github-actions%5Bbot%5D&per_page=100&page={page}")
        matches += [i for i in items if "pull_request" not in i and marker in (i.get("body") or "")]
        if len(items) < 100:
            break
    if not details:
        for item in matches:
            api(f"repos/{REPO}/issues/{item['number']}", "PATCH", {"state": "closed", "state_reason": "completed"})
        return
    digest = hashlib.sha256(details.encode()).hexdigest()
    body = marker + f"\n<!-- findings:{digest} -->\n\n" + details
    if matches:
        item = matches[0]
        if f"<!-- findings:{digest} -->" not in (item.get("body") or ""):
            api(f"repos/{REPO}/issues/{item['number']}", "PATCH", {"title": title, "body": body})
    else:
        api(f"repos/{REPO}/issues", "POST", {"title": title, "body": body})


def source_alert(report):
    findings = []
    for row in report["sources"]:
        if not row["ok"]:
            findings.append(f"- Unavailable: {row['url']} ({row['failure_kind']}).")
    for url in report["pending_review_sources"]:
        findings.append(f"- Source changed; review affected guides: {url}")
    details = "\n".join(sorted(findings))
    if details:
        details = ("The daily source monitor detected the following findings. Last successful observations are retained. "
                   "Review and test affected guides before clearing their pending state.\n\n" + details +
                   f"\n\n[Full source status](https://github.com/{REPO}/blob/main/docs/UPSTREAM_STATUS.md).")
    issue("source-drift", "Upstream source changes or availability need review", details)


def start_validation(number, sha, branch=BRANCH, author="github-actions[bot]"):
    """Approve only this generated PR's exact validation run, using actions:write.

    Dispatch checks are useful diagnostics but GitHub does not evaluate them as
    required PR checks. The native pull_request run must actually be started.
    """
    for attempt in range(10):
        runs = api(f"repos/{REPO}/actions/workflows/validate.yml/runs?event=pull_request&head_sha={sha}&per_page=20")
        for run in runs["workflow_runs"]:
            if (run["head_sha"] != sha or run["event"] != "pull_request" or
                run["head_repository"]["full_name"] != REPO or
                run["path"] != ".github/workflows/validate.yml" or
                run["actor"]["login"] not in {"github-actions[bot]", "dependabot[bot]"} or
                not any(p["number"] == number and p["head"]["ref"] == branch for p in run["pull_requests"])):
                continue
            snapshot = api(f"repos/{REPO}/pulls/{number}")
            if (snapshot["head"]["sha"] != sha or snapshot["head"]["ref"] != branch or
                snapshot["user"]["login"] != author or snapshot["state"] != "open"):
                raise RuntimeError("Generated PR changed before validation approval")
            if run["conclusion"] == "action_required":
                api(f"repos/{REPO}/actions/runs/{run['id']}/approve", "POST")
            print(json.dumps({"validation_run": run["html_url"], "event": "pull_request"}))
            return
        if attempt < 9:
            time.sleep(4)
    raise RuntimeError("No native validation run appeared for the generated PR")


def dependency_paths():
    allowed = {"requirements-dev.txt", "package.json", "package-lock.json"}
    for folder in ["telegram-bot-python-telegram-bot/assets/starter", "telegram-bot-aiogram/assets/starter",
                   "telegram-bot-telethon/assets/starter", "telegram-bot-recipes/assets"]:
        allowed.add(f"{folder}/requirements.txt")
    for folder in ["telegram-bot-go-botapi/assets/go-telegram-echo", "telegram-bot-go-botapi/assets/gotgbot-echo",
                   "telegram-bot-go-botapi/assets/classic-echo", "telegram-bot-gotd/assets/echo",
                   "telegram-bot-gotd-contrib/assets/reliable-echo"]:
        allowed.update(f"{folder}/{name}" for name in ["go.mod", "go.sum"])
    allowed.update({"telegram-bot-javascript/assets/starter/package.json",
                    "telegram-bot-javascript/assets/starter/package-lock.json",
                    "telegram-bot-java/assets/echo/pom.xml",
                    "telegram-bot-dotnet/assets/starter/TelegramStarter.csproj",
                    "telegram-bot-dotnet/assets/starter/packages.lock.json",
                    "telegram-bot-php/assets/starter/composer.json",
                    "telegram-bot-php/assets/starter/composer.lock",
                    "telegram-bot-rust/assets/echo/Cargo.toml",
                    "telegram-bot-rust/assets/echo/Cargo.lock"})
    return allowed


def allowed_update_files(pr, author):
    """Recheck the complete current diff; retained auto-merge is not approval."""
    allowed = set(generated_paths()) if author == "github-actions[bot]" else dependency_paths()
    files = []
    for page in range(1, 31):
        batch = api(f"repos/{REPO}/pulls/{pr['number']}/files?per_page=100&page={page}")
        files.extend(batch)
        if len(batch) < 100:
            break
    if len(files) != pr["changed_files"] or not files:
        return False
    for item in files:
        path = item["filename"]
        if item["status"] not in {"modified", "added"}:
            return False
        if path in allowed:
            continue
        if author != "dependabot[bot]" or not path.startswith(".github/workflows/") or not path.endswith((".yml", ".yaml")):
            return False
        # Match the initial Dependabot gate: only immutable action references.
        changed = [line[1:] for line in item.get("patch", "").splitlines()
                   if line[:1] in "+-" and not line.startswith(("+++", "---"))]
        if item["status"] != "modified" or not changed or not all(re.fullmatch(
                r"\s*(?:-\s*)?uses:\s*[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{40}(?:\s+#.*)?\s*", line)
                for line in changed):
            return False
    return True


def maintain_updates(event_path):
    """Keep already eligible bot PRs current with main and start their native tests."""
    run = json.loads(Path(event_path).read_text(encoding="utf-8"))["workflow_run"]
    if run["repository"]["full_name"] != REPO or run["name"] != "Validate skill pack" or run["conclusion"] != "success":
        return
    protected()
    pulls = api(f"repos/{REPO}/pulls?state=open&base=main&per_page=100")
    for item in pulls:
        if not item.get("auto_merge") or item["user"]["login"] not in {"github-actions[bot]", "dependabot[bot]"}:
            continue
        pr = api(f"repos/{REPO}/pulls/{item['number']}")
        branch, author = pr["head"]["ref"], pr["user"]["login"]
        if pr["state"] != "open" or not pr.get("auto_merge") or author not in {"github-actions[bot]", "dependabot[bot]"}:
            continue
        if pr["head"]["repo"]["full_name"] != REPO or pr["base"]["ref"] != "main":
            continue
        if author == "github-actions[bot]" and branch != BRANCH:
            continue
        if pr.get("draft") or not allowed_update_files(pr, author):
            subprocess.run(["gh", "pr", "merge", str(pr["number"]), "--repo", REPO, "--disable-auto"], check=True)
            continue
        if pr["mergeable_state"] != "behind":
            continue
        # Only merge main after this exact head's current diff passed the policy.
        # The expected head prevents a concurrent change from being updated.
        old_sha = pr["head"]["sha"]
        api(f"repos/{REPO}/pulls/{pr['number']}/update-branch", "PUT", {"expected_head_sha": old_sha})
        for attempt in range(10):
            current = api(f"repos/{REPO}/pulls/{pr['number']}")
            if current["state"] != "open":
                break
            if current["head"]["sha"] != old_sha:
                start_validation(pr["number"], current["head"]["sha"], branch, author)
                break
            time.sleep(2)
        else:
            raise RuntimeError("Automated branch update did not become visible")


def publish(report_path):
    if os.environ.get("GITHUB_EVENT_NAME") not in {"schedule", "workflow_dispatch"} or os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise RuntimeError("Refresh publishing is restricted to the default branch")
    protected()
    main = api(f"repos/{REPO}/git/ref/heads/main")["object"]["sha"]
    local = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if local != main:
        raise RuntimeError("Main advanced during the scan; rerun from the current main")
    parent = api(f"repos/{REPO}/git/commits/{main}")
    tree = api(f"repos/{REPO}/git/trees/{parent['tree']['sha']}?recursive=1")
    if tree.get("truncated"):
        raise RuntimeError("Repository tree was truncated")
    old = {item["path"]: item["sha"] for item in tree["tree"] if item["type"] == "blob"}
    changes = []
    for name in generated_paths():
        path = ROOT / name
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT):
            raise RuntimeError("Generated path escaped the repository")
        content = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        raw = content.encode()
        digest = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if old.get(name) != digest:
            changes.append({"path": name, "mode": "100644", "type": "blob", "content": content})
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    if not changes:
        source_alert(report)
        print("Source observations are already current.")
        return
    pulls = api(f"repos/{REPO}/pulls?state=open&base=main&head=Aztech-1729:{BRANCH}")
    if any(p["user"]["login"] != "github-actions[bot]" for p in pulls):
        raise RuntimeError("The reserved automation branch belongs to another author")
    ref = api(f"repos/{REPO}/git/ref/heads/{BRANCH}", missing=True)
    if ref:
        prior = api(f"repos/{REPO}/git/commits/{ref['object']['sha']}")
        if prior["message"] != COMMIT:
            # The maintenance job may have merged main into this bot-owned PR.
            # Accept that branch only if its entire PR diff is generated evidence.
            if not pulls:
                raise RuntimeError("Refusing to replace a non-automation branch")
            files = api(f"repos/{REPO}/pulls/{pulls[0]['number']}/files?per_page=100")
            allowed = set(generated_paths())
            if len(files) != pulls[0]["changed_files"] or not files or any(f["filename"] not in allowed for f in files):
                raise RuntimeError("Refusing to replace a non-automation branch")
    new_tree = api(f"repos/{REPO}/git/trees", "POST", {"base_tree": parent["tree"]["sha"], "tree": changes})
    commit = api(f"repos/{REPO}/git/commits", "POST", {"message": COMMIT, "tree": new_tree["sha"], "parents": [main]})
    if api(f"repos/{REPO}/git/ref/heads/main")["object"]["sha"] != main:
        raise RuntimeError("Main advanced; generated results must be rebuilt")
    if ref:
        if api(f"repos/{REPO}/git/ref/heads/{BRANCH}")["object"]["sha"] != ref["object"]["sha"]:
            raise RuntimeError("Automation branch changed concurrently")
        api(f"repos/{REPO}/git/refs/heads/{BRANCH}", "PATCH", {"sha": commit["sha"], "force": True})
    else:
        api(f"repos/{REPO}/git/refs", "POST", {"ref": f"refs/heads/{BRANCH}", "sha": commit["sha"]})
    counts = report["counts"]
    body = ("Refresh generated source hashes, release observations and per-skill status. "
            "Skill instructions and editorial review dates are unchanged.\n\n"
            f"Checked {counts['total']} sources; {counts['unavailable']} unavailable; "
            f"{counts['pending_review']} unresolved source changes.\n\n"
            "Merge requires the full validation workflow. Unavailable sources preserve the last successful evidence. "
            "Content changes remain in the source review issue until reviewed and tested.")
    if pulls:
        pr = api(f"repos/{REPO}/pulls/{pulls[0]['number']}", "PATCH", {"body": body})
    else:
        pr = api(f"repos/{REPO}/pulls", "POST", {"title": "Refresh upstream source observations", "head": BRANCH, "base": "main", "body": body})
    subprocess.run(["gh", "pr", "merge", str(pr["number"]), "--repo", REPO, "--auto", "--squash",
                    "--match-head-commit", commit["sha"]], check=True)
    start_validation(pr["number"], commit["sha"])
    source_alert(report)
    print(json.dumps({"pull_request": pr["html_url"], "head_sha": commit["sha"], "changed_files": len(changes)}))


def alert(event_path):
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    run = event["workflow_run"]
    if run["repository"]["full_name"] != REPO or run["head_branch"] != "main":
        return
    if run["name"] not in {"Validate skill pack", "Refresh upstream evidence"}:
        return
    # Ignore a late notification from a run superseded by a newer completed run.
    latest = api(f"repos/{REPO}/actions/workflows/{run['workflow_id']}/runs?branch=main&status=completed&per_page=1")
    if latest["workflow_runs"] and latest["workflow_runs"][0]["id"] != run["id"]:
        return
    key = "workflow-" + str(run["workflow_id"])
    if run["conclusion"] == "success":
        issue(key, "", "")
    elif run["conclusion"] not in {"cancelled", "skipped"}:
        issue(key, f"Automation failed: {run['name']}",
              f"[{run['name']} run {run['run_number']}]({run['html_url']}) finished with {run['conclusion']}. "
              "Inspect the failing job and rerun after the cause is fixed. This issue closes after a successful default-branch run.")


def main():
    if os.environ.get("GITHUB_REPOSITORY") != REPO:
        raise RuntimeError("This publisher is restricted to its configured repository")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["publish", "alert", "maintain"])
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    {"publish": publish, "alert": alert, "maintain": maintain_updates}[args.command](args.path)


if __name__ == "__main__":
    main()
