"""Validate publishable pack files without network access or bot credentials."""
from __future__ import annotations
import ast
import json
from pathlib import Path
import re
import subprocess
import sys
import tomllib
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET
import yaml
import validate_plugins

ROOT = Path(__file__).resolve().parents[1]
SKILLS = sorted(ROOT.glob('telegram-bot-*/SKILL.md'))


def tracked_files():
    result = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                            cwd=ROOT, check=True, stdout=subprocess.PIPE)
    return sorted({ROOT / name for name in result.stdout.decode().split('\0') if name})


def anchors(text):
    result, counts = set(re.findall(r'<a\s+(?:name|id)=["\']([^"\']+)', text)), {}
    for line in text.splitlines():
        if not re.match(r'^#{1,6} ', line):
            continue
        title = re.sub(r'^#+\s+|\s+#+$', '', line).lower()
        title = re.sub(r'[^\w\- ]', '', title).replace(' ', '-')
        duplicate = counts.get(title, 0)
        counts[title] = duplicate + 1
        result.add(title + (f'-{duplicate}' if duplicate else ''))
    return result


def main():
    errors = []
    try:
        validate_plugins.validate(ROOT)
    except (ValueError, KeyError, TypeError, OSError, ET.ParseError) as exc:
        errors.append(f'Native plugin metadata: {exc}')
    if len(SKILLS) != 18:
        errors.append(f'Expected 18 skills, found {len(SKILLS)}; update catalog and validator together')
    for path in SKILLS:
        text = path.read_text(encoding='utf-8')
        parts = text.split('---', 2)
        try:
            if not text.startswith('---\n') or len(parts) != 3:
                raise ValueError('missing frontmatter')
            meta = yaml.safe_load(parts[1])
            if meta.get('name') != path.parent.name or not re.fullmatch(r'[a-z0-9-]{1,63}', meta['name']):
                raise ValueError('invalid or mismatched name')
            if not isinstance(meta.get('description'), str) or not meta['description'].strip():
                raise ValueError('missing description')
            for filename in ['guide.md', 'sources.md']:
                if not (path.parent / 'references' / filename).is_file():
                    raise ValueError(f'missing references/{filename}')
        except (ValueError, KeyError, TypeError, AttributeError, yaml.YAMLError) as exc:
            errors.append(f'{path.relative_to(ROOT)}: {exc}')
    files = tracked_files()
    for path in files:
        if not path.is_file():
            continue
        name = path.relative_to(ROOT).as_posix()
        try:
            content = path.read_text(encoding='utf-8')
        except UnicodeError:
            errors.append(f'{name}: unexpected binary file in source pack')
            continue
        try:
            if path.suffix == '.py':
                ast.parse(content, filename=name)
            elif path.suffix == '.json':
                json.loads(content)
            elif path.suffix == '.toml':
                tomllib.loads(content)
            elif path.suffix in {'.xml', '.csproj'}:
                ET.fromstring(content)
            elif path.suffix in {'.yml', '.yaml'}:
                yaml.safe_load(content)
        except (SyntaxError, ValueError, ET.ParseError, yaml.YAMLError) as exc:
            errors.append(f'{name}: syntax: {exc}')
        if re.search(r'gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,}', content):
            errors.append(f'{name}: possible GitHub credential')
        if re.search(r'\b[0-9]{8,12}:[A-Za-z0-9_-]{35}\b', content):
            errors.append(f'{name}: possible Telegram credential')
        if path.suffix != '.md':
            continue
        if 'search-result://' in content:
            errors.append(f'{name}: transient search-result citation')
        plain = re.sub(r'```.*?```', '', content, flags=re.S)
        for target in re.findall(r'\[[^\]]*\]\(([^\s)]+)(?:\s+"[^"]*")?\)', plain):
            target = target.strip('<>')
            parsed = urlsplit(target)
            if parsed.scheme or target.startswith('//'):
                continue
            destination = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
            if not destination.is_relative_to(ROOT):
                errors.append(f'{name}: link escapes repository: {target}')
            elif not destination.exists():
                errors.append(f'{name}: broken link: {target}')
            elif parsed.fragment and destination.suffix == '.md':
                if unquote(parsed.fragment) not in anchors(destination.read_text(encoding='utf-8')):
                    errors.append(f'{name}: missing anchor: {target}')
    if errors:
        print('\n'.join(errors))
        return 1
    print(f'PASS: {len(SKILLS)} skills; {len(files)} source files; metadata, local links, syntax and credential patterns')
    return 0


if __name__ == '__main__':
    sys.exit(main())
