#!/bin/bash
# Deadpool HUD - Antigravity Watchdog & Self-Healer Loop
# ───────────────────────────────────────────────────────
# This script monitors the connection and server status.
# If it finds a disconnect or a known error, it tries to heal it.

echo "⚔  DEADPOOL HUD: Automated Error Monitor & Self-Healer"
echo "👀 Monitoring started. Press Ctrl+C to stop."

while true; do
    echo "--- Checking Status $(date +%H:%M:%S) ---"

    # 1. Check if Laptop HUD Server is alive
    if ! pgrep -f "desktop_dashboard.py" > /dev/null; then
        echo "❌ Desktop HUD Server is DOWN. Restarting..."
        nohup python3 -u /home/kiyotoka/Dashy/desktop_dashboard.py > /tmp/hud_debug.log 2>&1 &
        sleep 2
    else
        echo "✅ Desktop Server Running."
    fi

    # 2. Check for ADB Device & Sync Reverse Port
    DEV=$(adb devices | grep -v "List" | grep "device")
    if [ -z "$DEV" ]; then
        echo "⚠️  Phone not detected via ADB! Check USB/Network ADB."
    else
        echo "✅ Phone Connected via ADB. Ensuring Port Reverse (8844)..."
        adb reverse tcp:8844 tcp:8844
    fi

    # 3. Analyze Recent Logs for specific errors
    # Check for 403 (HUD is offline on laptop)
    if tail -n 5 /tmp/hud_debug.log | grep "403" > /dev/null; then
        echo "💡 HINT: Laptop HUD is in 'OFFLINE' mode. Click the icon on your laptop taskbar to turn it on."
    fi

    # Check for Logcat Errors
    if [ ! -z "$DEV" ]; then
        adb logcat -d | grep -iE 'ReactNativeJS|HUD' | grep -iE 'Error|Exception' | tail -n 1
    fi

    echo "⏳ Sleeping for 10s..."
    sleep 10
done
