#!/usr/bin/env python3
"""Runs both Discord listener and Flask server, with auto-restart + backoff."""
import subprocess
import sys
import time

# Restart delay increases each time to avoid hammering Discord API
INITIAL_DELAY = 30       # 30 seconds first restart
MAX_DELAY = 600          # 10 minutes max
BACKOFF_MULTIPLIER = 2   # Double delay each failure
RESET_AFTER = 300        # Reset delay counter after 5 min of stable running


def start_process(name, args):
    print(f"[START] Starting {name}...", flush=True)
    return subprocess.Popen(
        args,
        stdout=sys.stdout,
        stderr=sys.stderr,
    ), time.time()


listener_proc, listener_started = start_process("Discord listener", [sys.executable, "discord_listener.py"])
server_proc, server_started = start_process("Flask server", [sys.executable, "server.py"])
listener_delay = INITIAL_DELAY
server_delay = INITIAL_DELAY

while True:
    time.sleep(5)

    if listener_proc.poll() is not None:
        uptime = time.time() - listener_started
        # Reset backoff if it ran for a while (was healthy)
        if uptime > RESET_AFTER:
            listener_delay = INITIAL_DELAY

        print(f"[FATAL] Discord listener exited (code {listener_proc.returncode}) after {uptime:.0f}s. "
              f"Waiting {listener_delay}s before restart...", flush=True)
        time.sleep(listener_delay)
        listener_proc, listener_started = start_process("Discord listener", [sys.executable, "discord_listener.py"])
        listener_delay = min(listener_delay * BACKOFF_MULTIPLIER, MAX_DELAY)

    if server_proc.poll() is not None:
        uptime = time.time() - server_started
        if uptime > RESET_AFTER:
            server_delay = INITIAL_DELAY

        print(f"[FATAL] Flask server exited (code {server_proc.returncode}) after {uptime:.0f}s. "
              f"Waiting {server_delay}s before restart...", flush=True)
        time.sleep(server_delay)
        server_proc, server_started = start_process("Flask server", [sys.executable, "server.py"])
        server_delay = min(server_delay * BACKOFF_MULTIPLIER, MAX_DELAY)
