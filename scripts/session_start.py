#!/usr/bin/env python3
"""
session_start.py - Generates a machine-readable session brief for TRL RTX Remix.
Run at the start of every Claude session: python scripts/session_start.py
"""
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent


def read_tail(path, lines=60):
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            content = f.readlines()
        return ''.join(content[-lines:])
    except FileNotFoundError:
        return None


def read_head(path, lines=60):
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            content = f.readlines()
        return ''.join(content[:lines])
    except FileNotFoundError:
        return None


def get_highest_build():
    test_dir = ROOT / 'TRL tests'
    if not test_dir.exists():
        return 'none'
    folders = [f.name for f in test_dir.iterdir() if f.is_dir() and f.name.startswith('build-')]
    numbers = []
    for folder in folders:
        m = re.match(r'build-(\d+)', folder)
        if m:
            numbers.append(int(m.group(1)))
    return str(max(numbers)).zfill(3) if numbers else 'none'


def get_last_changelog_entry():
    cl = read_tail(ROOT / 'CHANGELOG.md', 80)
    if not cl:
        return 'No CHANGELOG.md found.'
    lines = cl.split('\n')
    entry_lines = []
    in_entry = False
    for line in lines:
        if re.match(r'^#{1,3}\s+\d{4}-\d{2}-\d{2}', line):
            if in_entry:
                break
            in_entry = True
        if in_entry:
            entry_lines.append(line)
    return '\n'.join(entry_lines[:20]) if entry_lines else 'No dated entries found.'


def count_dead_ends():
    claude_md = read_head(ROOT / 'CLAUDE.md', 400)
    if not claude_md:
        return 0
    rows = re.findall(r'^\|\s*\d+', claude_md, re.MULTILINE)
    return len(rows)


def main():
    today = date.today().isoformat()
    build = get_highest_build()
    next_build = str(int(build) + 1).zfill(3) if build.isdigit() else '???'
    dead_ends = count_dead_ends()

    test_dir = ROOT / 'TRL tests'
    build_count = len(list(test_dir.glob('build-*'))) if test_dir.exists() else 0

    sep = '=' * 58
    print(f'\n{sep}')
    print(f'  SESSION BRIEF — TRL RTX Remix — {today}')
    print(f'{sep}\n')

    wb = read_head(ROOT / 'docs' / 'status' / 'WHITEBOARD.md') or read_head(ROOT / 'WHITEBOARD.md')
    if wb:
        print('WHITEBOARD (top 25 lines):')
        print('\n'.join(wb.split('\n')[:25]))
        print()

    print('LAST CHANGELOG ENTRY:')
    print(get_last_changelog_entry())
    print()

    print(f'BUILD STATUS:')
    print(f'  Highest build:    #{build}')
    print(f'  Next build will:  #{next_build}')
    print(f'  Build archive:    {build_count} folders in TRL tests/')
    print(f'  Dead ends logged: {dead_ends}')
    print()

    handoff = read_head(ROOT / 'HANDOFF.md', 20)
    if handoff:
        print('HANDOFF NOTE (top 15 lines):')
        print('\n'.join(handoff.split('\n')[:15]))
        print()

    print('QUICK COMMANDS:')
    print('  python verify_install.py')
    print('  python patches/TombRaiderLegend/run.py test-hash --build')
    print('  python patches/TombRaiderLegend/run.py test --build --randomize')
    print('  python -m autopatch')
    print(f'\n{sep}\n')


if __name__ == '__main__':
    main()
