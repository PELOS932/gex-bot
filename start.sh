#!/bin/bash
# Run both processes with output visible in logs
python3 discord_listener.py 2>&1 &
LISTENER_PID=$!
echo "[START] Discord listener PID: $LISTENER_PID"

python3 server.py 2>&1 &
SERVER_PID=$!
echo "[START] Flask server PID: $SERVER_PID"

# Wait for either to die
while true; do
    if ! kill -0 $LISTENER_PID 2>/dev/null; then
        echo "[FATAL] Discord listener crashed! Restarting..."
        python3 discord_listener.py 2>&1 &
        LISTENER_PID=$!
        echo "[START] Restarted listener PID: $LISTENER_PID"
    fi
    if ! kill -0 $SERVER_PID 2>/dev/null; then
        echo "[FATAL] Flask server crashed! Restarting..."
        python3 server.py 2>&1 &
        SERVER_PID=$!
        echo "[START] Restarted server PID: $SERVER_PID"
    fi
    sleep 5
done
