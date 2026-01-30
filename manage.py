#!/usr/bin/env python
from os import environ
from pathlib import Path
from sys import argv

if __name__ == "__main__":
    # Use docker secrets for default values if they are available
    secrets = Path("/run/secrets")
    if secrets.is_dir():
        for filepath in secrets.iterdir():
            with open(filepath, "r") as file:
                key = filepath.name
                value = file.read().strip()
                environ.setdefault(key, value)

    # Production is default for safety
    environ.setdefault("DJANGO_SETTINGS_MODULE", "TWLight.settings.production")
    from django.core.management import execute_from_command_line

    execute_from_command_line(argv)
