#!/usr/bin/env python3
"""Exercise the real skills CLI in temporary projects; preserve every skill file."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def skill_files(root=ROOT):
    names = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=root
    ).decode().split("\0")
    skills = {p.parent.name for p in root.glob("telegram-bot-*/SKILL.md")}
    files = {name: root / name for name in names if name and Path(name).parts[0] in skills}
    if any(path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) for path in files.values()):
        raise ValueError("Skill resources must be contained regular source files")
    return files


def verify_install(source_files, target, allowed_root=None):
    """Verify text contents and local Markdown routes in the installed full pack."""
    failures = []
    allowed_root = (allowed_root or target).resolve()
    for name, source in source_files.items():
        installed = target / name
        if not installed.resolve().is_relative_to(allowed_root):
            failures.append("Installed resource escapes the test project: " + name)
            continue
        if not installed.is_file():
            failures.append("Missing installed resource: " + name)
            continue
        # Git normalizes this repository's text resources to LF. A Windows
        # checkout may contain CRLF before the same files are published.
        if installed.read_bytes().replace(b"\r\n", b"\n") != source.read_bytes().replace(b"\r\n", b"\n"):
            failures.append("Installed resource differs: " + name)
        if installed.suffix != ".md":
            continue
        plain = re.sub(r"```.*?```", "", installed.read_text(encoding="utf-8"), flags=re.S)
        for link in re.findall(r"\[[^\]]*\]\(([^\s)]+)(?:\s+\"[^\"]*\")?\)", plain):
            parsed = urlsplit(link.strip("<>"))
            if parsed.scheme or link.startswith("//") or not parsed.path:
                continue
            destination = (installed.parent / unquote(parsed.path)).resolve()
            if not destination.is_relative_to(allowed_root) or not destination.exists():
                failures.append(f"Unavailable installed local route: {name}: {link}")
    if failures:
        raise ValueError("\n".join(failures[:30]))


def check(root=ROOT, remote_source=None):
    cli = root / "node_modules/skills/bin/cli.mjs"
    if not cli.is_file():
        raise ValueError("Run npm ci --ignore-scripts first to install the locked test tool")
    node = shutil.which("node")
    if not node:
        raise ValueError("Node.js is required for the installation smoke check")
    files = skill_files(root)
    names = {Path(name).parts[0] for name in files}
    if len(names) != 18 or not all(f"{name}/SKILL.md" in files for name in names):
        raise ValueError("Expected all 18 complete source skills")
    version = json.loads((root / "node_modules/skills/package.json").read_text(encoding="utf-8"))["version"]
    results = []
    with TemporaryDirectory(prefix="telegram-install-") as directory:
        temporary = Path(directory)
        source = temporary / "source"
        for name, path in files.items():
            destination = source / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
        for mode, flags in (
            ("all-supported-agents", ["--all"]),
            ("codex-claude-opencode-copy", ["--skill", "*", "--agent", "codex", "claude-code", "opencode", "--yes", "--copy"]),
        ):
            project = temporary / mode
            project.mkdir()
            command = [node, str(cli), "add", remote_source or str(source), *flags, "--json"]
            result = subprocess.run(command, cwd=project, text=True, capture_output=True, timeout=240, check=False)
            if result.returncode:
                raise ValueError(f"Real skills CLI failed in {mode} (exit {result.returncode})")
            for folder in (".agents/skills", ".claude/skills"):
                verify_install(files, project / folder, project)
            # Both Codex and OpenCode discover the shared .agents/skills tree;
            # Claude's own tree is checked for both links and independent copies.
            results.append({"mode": mode, "skills": len(names), "resources_verified": len(files),
                            "local_markdown_routes": "passed"})
    return {"skills_cli_version": version, "scope": "temporary projects", "results": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-source", help="Also exercise a published GitHub source instead of the clean local staging tree")
    args = parser.parse_args()
    try:
        print(json.dumps(check(remote_source=args.remote_source), indent=2))
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
