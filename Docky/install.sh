#!/bin/bash
# Install Docky as the primary startup controller

echo "⚔️  DOCKY: Initializing Master Controller..."

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
SYSTEMD_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_DIR"

# 1. Cleanup all other Bubbly services
echo "🧹 Cleaning up old services..."
systemctl --user stop locky.service 2>/dev/null
systemctl --user disable locky.service 2>/dev/null
pkill -f "python3.*main.py" 2>/dev/null
pkill -f "python3.*desktop_dashboard.py" 2>/dev/null

# 2. Configure Docky Service
echo "⚙️  Configuring Docky Service..."
cp "$DIR/docky.service" "$SYSTEMD_DIR/docky.service"

# 3. Enable and Start
echo "🚀 Launching Master Controller..."
systemctl --user daemon-reload
systemctl --user enable docky.service
systemctl --user restart docky.service

echo "✅ DONE! Docky will now start automatically at login."
echo "   All other individual bubble services have been disabled."
echo "   Use Docky to manage your bubbles from now on."
