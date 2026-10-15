#!/usr/bin/env python3
"""Validate local template values without displaying credentials."""
from pathlib import Path
import sys

path = Path(__file__).resolve().parents[1] / ".local/credentials.env"
required = {"ADMIN_EMAIL", "ADMIN_PASSWORD", "SQL_PASSWORD", "API_USER_EMAIL", "API_CLIENT_ID", "API_CLIENT_SECRET"}
try:
    lines = path.read_text(encoding="utf-8").splitlines()
    values = dict(line.split("=", 1) for line in lines)
    if len(lines) != len(required) or set(values) != required:
        raise ValueError("credential file has missing, duplicate, or malformed keys")
    for key in required:
        if not values[key].strip():
            raise ValueError(f"{key} cannot be empty")
    if not values["API_CLIENT_ID"].startswith("umbraco-back-office-") or \
            values["API_CLIENT_ID"] == "umbraco-back-office-":
        raise ValueError("API_CLIENT_ID must start with umbraco-back-office- and have a suffix")
    if "@" not in values["ADMIN_EMAIL"] or "@" not in values["API_USER_EMAIL"]:
        raise ValueError("ADMIN_EMAIL and API_USER_EMAIL must be email addresses")
    sql_password = values["SQL_PASSWORD"]
    categories = (
        any("A" <= char <= "Z" for char in sql_password),
        any("a" <= char <= "z" for char in sql_password),
        any("0" <= char <= "9" for char in sql_password),
        any(not char.isalnum() for char in sql_password),
    )
    if not 8 <= len(sql_password) <= 128 or sum(categories) < 3:
        raise ValueError("SQL_PASSWORD must be 8-128 characters and use three of uppercase, lowercase, digits, and symbols")
    path.chmod(0o600)
except (OSError, ValueError) as error:
    print(f"Template credentials invalid: {error}", file=sys.stderr)
    sys.exit(1)
