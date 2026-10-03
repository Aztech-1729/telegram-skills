#!/usr/bin/env python3
"""Validate native plugin metadata against the pack's canonical skill folders."""
import argparse
import json
from pathlib import Path, PurePosixPath
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/Aztech-1729/telegram-skills"
MANIFESTS = (".codex-plugin/plugin.json", ".claude-plugin/plugin.json")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(root, name):
    path = root / name
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Manifest path escapes the pack: {name}")
    result = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    if not isinstance(result, dict):
        raise ValueError(f"Expected a JSON object: {name}")
    return result


def contained_path(root, name):
    if not isinstance(name, str) or not name.startswith("./") or "\\" in name:
        raise ValueError("Plugin paths must start with ./ and use forward slashes")
    parts = name[2:].split("/")
    if any(part in {"..", ".", ""} for part in parts) or PurePosixPath(name).is_absolute():
        raise ValueError(f"Invalid plugin component path: {name}")
    path = root / name[2:]
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or not path.exists():
        raise ValueError(f"Missing or escaping plugin component: {name}")
    return path


def validate(root=ROOT):
    root = Path(root).resolve()
    expected = sorted("./" + p.parent.name for p in root.glob("telegram-bot-*/SKILL.md"))
    if not expected:
        raise ValueError("No canonical Telegram skills found")
    codex, claude = (read_json(root, name) for name in MANIFESTS)
    shared = ("name", "version", "description", "author", "homepage", "repository", "keywords", "skills")
    if any(codex.get(key) != claude.get(key) for key in shared):
        raise ValueError("Codex and Claude plugin identities or skill lists differ")
    for name, manifest in zip(MANIFESTS, (codex, claude)):
        if (manifest.get("name") != "telegram" or manifest.get("repository") != REPOSITORY or
                manifest.get("homepage") != REPOSITORY or not manifest.get("author", {}).get("name") or
                not isinstance(manifest.get("version"), str) or
                not re.fullmatch(r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", manifest["version"])):
            raise ValueError(f"Invalid plugin identity: {name}")
        skills = manifest.get("skills")
        if not isinstance(skills, list) or skills != expected:
            raise ValueError(f"Plugin must include every canonical skill exactly once in sorted order: {name}")
        for skill in skills:
            path = contained_path(root, skill)
            if not path.is_dir() or not (path / "SKILL.md").is_file():
                raise ValueError(f"Plugin skill is incomplete: {skill}")
        if any(key in manifest for key in ("hooks", "commands", "agents", "mcpServers", "apps", "dependencies")):
            raise ValueError(f"Unexpected executable/service component in the skills-only package: {name}")
    if (root / "plugin.json").exists():
        raise ValueError("A portable root manifest would override custom canonical skill paths")
    interface = codex.get("interface", {})
    for key in ("displayName", "shortDescription", "longDescription", "developerName", "category"):
        if not isinstance(interface.get(key), str) or not interface[key].strip():
            raise ValueError(f"Missing Codex listing field: {key}")
    if len(interface["displayName"]) > 30 or len(interface["shortDescription"]) > 30:
        raise ValueError("Codex display name/subtitle exceeds its listing limit")
    if not isinstance(interface.get("capabilities"), list):
        raise ValueError("Missing Codex capabilities list")
    for key in ("composerIcon", "logo"):
        icon = contained_path(root, interface.get(key))
        if not icon.is_file() or icon.suffix != ".svg" or icon.stat().st_size > 5 * 1024 * 1024:
            raise ValueError(f"Invalid bundled SVG: {key}")
        svg = ET.fromstring(icon.read_text(encoding="utf-8"))
        box = [float(value) for value in svg.attrib.get("viewBox", "").split()]
        if len(box) != 4 or box[2] != box[3] or box[2] < 48:
            raise ValueError("Plugin icons must have a square viewBox of at least 48")
    marketplace = read_json(root, ".agents/plugins/marketplace.json")
    legacy = read_json(root, ".claude-plugin/marketplace.json")
    if (marketplace.get("name") != "aztech" or legacy.get("name") != "aztech" or
            not legacy.get("owner", {}).get("name")):
        raise ValueError("Invalid Aztech marketplace identity")
    for catalog in (marketplace, legacy):
        plugins = catalog.get("plugins")
        if not isinstance(plugins, list) or len(plugins) != 1 or plugins[0].get("name") != "telegram":
            raise ValueError("Marketplace must expose only telegram@aztech")
    entry = marketplace["plugins"][0]
    if (entry.get("source") != {"source": "local", "path": "./"} or
            entry.get("policy") != {"installation": "AVAILABLE", "authentication": "ON_INSTALL"} or
            entry.get("category") != "Developer Tools"):
        raise ValueError("Codex marketplace must install the complete pack root with explicit policies")
    entry = legacy["plugins"][0]
    if entry.get("source") != "./" or entry.get("strict") is not True:
        raise ValueError("Claude marketplace must install the complete pack root and use its manifest")
    if any(key in entry for key in ("skills", "commands", "hooks", "agents", "mcpServers")):
        raise ValueError("Claude marketplace must not override plugin components")
    return {"plugin": "telegram@aztech", "version": codex["version"], "skills": len(expected)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(validate(args.root)))
        return 0
    except (ValueError, KeyError, TypeError, OSError, ET.ParseError) as exc:
        print(f"Plugin validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
