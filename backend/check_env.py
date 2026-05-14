"""
Run before starting the server to verify all required keys are present.
Usage:  python check_env.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)

REQUIRED = {
    "OPENAI_API_KEY": {
        "hint": "Get from https://platform.openai.com/api-keys",
        "check": lambda v: v.startswith("sk-") and len(v) > 20,
        "check_msg": "must start with 'sk-' and be longer than 20 chars",
    },
    "GOOGLE_CLIENT_ID": {
        "hint": "Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client ID",
        "check": lambda v: v.endswith(".apps.googleusercontent.com"),
        "check_msg": "must end with '.apps.googleusercontent.com'",
    },
    "GOOGLE_CLIENT_SECRET": {
        "hint": "Same credential page as GOOGLE_CLIENT_ID",
        "check": lambda v: len(v) >= 10,
        "check_msg": "must not be empty",
    },
}

OPTIONAL = {
    "TELEGRAM_BOT_TOKEN": "Get from @BotFather on Telegram",
    "BACKEND_PORT": "Defaults to 8000",
    "LOG_LEVEL": "Defaults to 'info'",
}

GREEN = "\033[92m"
RED   = "\033[91m"
YELLOW= "\033[93m"
BOLD  = "\033[1m"
RESET = "\033[0m"

ok = True

print(f"\n{BOLD}── .env validation ({'found' if ENV_PATH.exists() else 'NOT FOUND — create backend/.env from .env.example'}) ──{RESET}")
if not ENV_PATH.exists():
    print(f"{RED}  backend/.env does not exist.{RESET}")
    print(f"  Run:  copy .env.example .env   (then fill in values)\n")
    sys.exit(1)

print(f"\n{BOLD}Required keys:{RESET}")
for key, meta in REQUIRED.items():
    val = os.getenv(key, "")
    if not val:
        print(f"  {RED}MISSING{RESET}  {key}")
        print(f"           {meta['hint']}")
        ok = False
    elif not meta["check"](val):
        print(f"  {YELLOW}INVALID{RESET}  {key}  ({meta['check_msg']})")
        ok = False
    else:
        masked = val[:8] + "…" + val[-4:] if len(val) > 14 else "***"
        print(f"  {GREEN}  OK   {RESET}  {key}  ({masked})")

print(f"\n{BOLD}Optional keys:{RESET}")
for key, hint in OPTIONAL.items():
    val = os.getenv(key, "")
    status = f"{GREEN}set{RESET}" if val else f"{YELLOW}not set{RESET}"
    print(f"  {status}     {key}  {'— ' + hint if not val else ''}")

print()
if ok:
    print(f"{GREEN}{BOLD}All required keys are present. Safe to start the server.{RESET}\n")
    sys.exit(0)
else:
    print(f"{RED}{BOLD}Fix the issues above in backend/.env before starting.{RESET}\n")
    sys.exit(1)
