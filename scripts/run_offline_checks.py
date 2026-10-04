"""Run each suite in its own process to avoid example-module name collisions."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SUITES = [
    ('telegram-bot-python-telegram-bot/assets/starter', ['offline_check.py']),
    ('telegram-bot-aiogram/assets/starter', ['offline_check.py']),
    ('telegram-bot-telethon/assets/starter', ['offline_check.py']),
    ('telegram-bot-keyboards-ui/scripts', ['-m', 'unittest', 'discover', '-p', 'test_*.py']),
    ('telegram-bot-accessibility/scripts', ['-m', 'unittest', 'discover', '-p', 'test_*.py']),
    ('telegram-bot-miniapps/scripts', ['-m', 'unittest', 'discover', '-p', 'test_*.py']),
    ('telegram-bot-payments-stars/scripts', ['-m', 'unittest', 'discover', '-p', 'test_*.py']),
    ('telegram-bot-advanced-features/scripts', ['-m', 'unittest', 'discover', '-p', 'test_*.py']),
    ('telegram-bot-rich-messaging', ['-m', 'unittest', 'discover', '-s', 'tests']),
    ('telegram-bot-recipes', ['-m', 'unittest', 'discover', '-s', 'tests']),
]


def main():
    failed = []
    for directory, args in SUITES:
        print(f'Checking {directory}', flush=True)
        result = subprocess.run([sys.executable, *args], cwd=ROOT / directory)
        if result.returncode:
            failed.append(directory)
    if failed:
        print('FAILED: ' + ', '.join(failed))
        return 1
    print(f'PASS: {len(SUITES)} isolated offline suites; no live bot calls')
    return 0


if __name__ == '__main__':
    sys.exit(main())
