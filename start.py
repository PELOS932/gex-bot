#!/usr/bin/env python3
"""Runs both Discord listener and Flask server, with auto-restart."""
import subprocess
import sys
import time

def start_process(name, args):
    print(f"[START] Starting {name}...", flush=True)
    return subprocess.Popen(
        args,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

listener = start_process("Discord listener", [sys.executable, "discord_listener.py"])
server = start_process("Flask server", [sys.executable, "server.py"])

while True:
    time.sleep(5)
    if listener.poll() is not None:
        print(f"[FATAL] Discord listener exited (code {listener.returncode}). Restarting...", flush=True)
        listener = start_process("Discord listener", [sys.executable, "discord_listener.py"])
    if server.poll() is not None:
        print(f"[FATAL] Flask server exited (code {server.returncode}). Restarting...", flush=True)
        server = start_process("Flask server", [sys.executable, "server.py"])
