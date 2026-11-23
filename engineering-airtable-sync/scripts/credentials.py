#!/usr/bin/env python3
"""Store an Airtable PAT from a local terminal, never from agent chat."""
import getpass
import os
from pathlib import Path
import platform
import subprocess
import sys

HOME = Path.home() / '.config' / 'engineering-airtable-sync'
SERVICE = 'engineering-airtable-sync'


def main():
    if not sys.stdin.isatty():
        raise SystemExit('Run this command directly in a terminal so the token prompt stays private.')
    if platform.system() == 'Darwin':
        # macOS security prompts for the secret itself. Never put the PAT in
        # Python memory, shell history, a subprocess argument, or agent output.
        command = ['/usr/bin/security', 'add-generic-password', '-U', '-s', SERVICE,
                   '-a', getpass.getuser(), '-w']
        print('Airtable PAT will be entered privately into the macOS Keychain prompt.')
        result = subprocess.run(command)
        if result.returncode:
            raise SystemExit('Could not store the PAT in macOS Keychain.')
    else:
        print('Enter the Airtable PAT below. Input is hidden; it will be stored in a 0600 file.')
        value = getpass.getpass('Airtable PAT: ').strip()
        if not value.startswith('pat') or len(value) < 20:
            raise SystemExit('That does not look like an Airtable Personal Access Token; nothing was saved.')
        HOME.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(HOME, 0o700)
        path = HOME / 'token'
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(value + '\n')
        os.chmod(path, 0o600)
    print('Airtable credential stored locally. The token was not displayed.')


if __name__ == '__main__':
    main()
