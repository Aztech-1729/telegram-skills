#!/usr/bin/env python3
"""Publish generated evidence and deduplicated alerts using the job's GITHUB_TOKEN."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

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
    contexts = branch.get("protection", {}).get("required_status_checks", {}).get("contexts", [])
    if not branch.get("protected") or "validation" not in contexts:
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
    # GITHUB_TOKEN pushes do not recursively trigger CI; dispatch the exact branch explicitly.
    api(f"repos/{REPO}/actions/workflows/validate.yml/dispatches", "POST", {"ref": BRANCH})
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
    parser.add_argument("command", choices=["publish", "alert"])
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    (publish if args.command == "publish" else alert)(args.path)


if __name__ == "__main__":
    main()
