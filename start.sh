#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
#  Revlv CEO Dashboard — Start Script
#
#  Forcibly closes any existing dashboard instances (Chrome app
#  windows and the HTTP server), then starts fresh.
#
#  Run:  bash ~/Documents/Claude/Projects/revlv-ceo-dashboard/start.sh
# ═══════════════════════════════════════════════════════════════════

export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT=3000
PLIST_NAME="com.revlv.ceodashboard"
PLIST_DEST="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"
LOG="/tmp/revlv-dashboard.log"
PYTHON="/usr/bin/python3"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DASH_URL="http://localhost:${PORT}/?fresh=1"
# Dedicated Chrome profile so the dashboard runs as its OWN isolated instance.
# This makes Chrome fully quit when the dashboard window closes (no leftover dock
# icon), and keeps it separate from your everyday browsing.
CHROME_PROFILE="$HOME/Library/Application Support/RevlvCEODashboard/chrome"
mkdir -p "$CHROME_PROFILE" 2>/dev/null || true

echo ""
echo "  ██████╗ ╗██╗     ██ ██╗    ██╗"
echo "  ██╔══██╗╝██║     ██ ██║    ██║"
echo "  ██████╔╝  ██║   ██ ║██║    ██║"
echo "  ██╔══██╗  ╚██╗ ██╔ ╝██║    ╚═╝"
echo "  ██║  ██║█╗ ╚███╔╝   ███████╗██╗"
echo "  ╚═╝  ╚═╝╚══════╝  ╚═══╝  ╚══════╝╚═╝"
echo ""
echo "  CEO Dashboard — Starting Fresh"
echo "  ─────────────────────────────────────"

# ══════════════════════════════════════════════════════
#  STEP 1 — Kill all existing dashboard Chrome windows
# ══════════════════════════════════════════════════════
echo ""
echo "  ⏳ Closing existing dashboard windows..."

# Kill any Chrome windows running the dashboard app
# Works for both --app= mode and regular tab mode
/usr/bin/osascript << 'APPLESCRIPT' 2>/dev/null
tell application "Google Chrome"
    set windowList to every window
    repeat with w in windowList
        set tabList to every tab of w
        repeat with t in tabList
            if URL of t contains "localhost:3000" then
                delete t
            end if
        end repeat
    end repeat
end tell
APPLESCRIPT

# Also kill any standalone Chrome app-mode windows for localhost:3000
# (--app= mode creates a separate process; find and kill it)
/bin/ps aux 2>/dev/null | /usr/bin/grep -i "chrome.*localhost:3000" | /usr/bin/grep -v grep \
  | /usr/bin/awk '{print $2}' | xargs /bin/kill 2>/dev/null || true

sleep 0.5
echo "  ✅ Existing windows closed"

# ══════════════════════════════════════════════════════
#  STEP 2 — Stop the existing HTTP server
# ══════════════════════════════════════════════════════
echo ""
echo "  ⏳ Stopping existing server on port ${PORT}..."

# Stop via LaunchAgent and fully unload it, so an updated plist
# (now pointing at server.py) is picked up on the next bootstrap.
if [ -f "$PLIST_DEST" ]; then
    /bin/launchctl stop "${PLIST_NAME}" 2>/dev/null || true
    /bin/launchctl bootout "gui/$(/usr/bin/id -u)/${PLIST_NAME}" 2>/dev/null || true
fi

# Hard-kill anything on the port as a fallback
/usr/sbin/lsof -ti tcp:${PORT} 2>/dev/null | xargs /bin/kill -9 2>/dev/null || true
sleep 0.5

echo "  ✅ Server stopped"

# ══════════════════════════════════════════════════════
#  STEP 3 — Start the server fresh
# ══════════════════════════════════════════════════════
echo ""
echo "  ⏳ Starting fresh server on port ${PORT}..."

# Truncate old log so it starts clean
echo "--- Dashboard started $(date) ---" > "$LOG"

# Refresh the installed LaunchAgent from the repo so the server.py wiring is current
/bin/mkdir -p "$HOME/Library/LaunchAgents"
/bin/cp "$SCRIPT_DIR/${PLIST_NAME}.plist" "$PLIST_DEST" 2>/dev/null || true

# Try LaunchAgent first (preferred — auto-restart on crash)
if [ -f "$PLIST_DEST" ]; then
    /bin/launchctl bootstrap "gui/$(/usr/bin/id -u)" "$PLIST_DEST" 2>/dev/null || \
    /bin/launchctl load -w "$PLIST_DEST" 2>/dev/null || true
    sleep 1.5
fi

# Fall back to direct Python start if LaunchAgent didn't work
if ! /usr/bin/curl -sf --connect-timeout 2 "http://localhost:${PORT}/" -o /dev/null; then
    (
        cd "$SCRIPT_DIR" || exit 1
        nohup "$PYTHON" "$SCRIPT_DIR/server.py" >> "$LOG" 2>&1 &
        disown $!
    )
    # Wait up to 10 seconds for server to respond
    for i in $(seq 1 20); do
        sleep 0.5
        /usr/bin/curl -sf --connect-timeout 1 "http://localhost:${PORT}/" -o /dev/null && break
    done
fi

if ! /usr/bin/curl -sf --connect-timeout 3 "http://localhost:${PORT}/" -o /dev/null; then
    echo "  ❌ Server failed to start. Check: cat ${LOG}"
    echo "     Run setup again: bash ${SCRIPT_DIR}/setup.sh"
    exit 1
fi

echo "  ✅ Server is live at http://localhost:${PORT}"

# ══════════════════════════════════════════════════════
#  STEP 4 — Open dashboard in Chrome (fresh instance)
# ══════════════════════════════════════════════════════
echo ""
echo "  🚀 Launching fresh CEO Dashboard in Chrome..."
sleep 0.3   # brief pause so any killed window fully exits

if [ -f "$CHROME" ]; then
    "$CHROME" \
        --user-data-dir="$CHROME_PROFILE" \
        --app="$DASH_URL" \
        --start-fullscreen \
        --new-window \
        --disable-translate \
        --no-first-run \
        --no-default-browser-check \
        --noerrdialogs \
        --disable-features=TranslateUI \
        2>/dev/null &
    disown $!
else
    /usr/bin/open -na "Google Chrome" --args \
        --user-data-dir="$CHROME_PROFILE" \
        --app="$DASH_URL" \
        --start-fullscreen \
        --new-window \
        --disable-translate \
        --no-first-run \
        --no-default-browser-check \
        --noerrdialogs
fi

echo "  ✅ Dashboard launched — login screen ready."
echo ""
echo "  ─────────────────────────────────────────────────────"
echo "  ▶  Login screen is always shown on fresh start"
echo "  ▶  Server runs in background (auto-restarts on crash)"
echo "  ▶  Useful commands:"
echo "     Status:  launchctl list | grep revlv"
echo "     Logs:    cat /tmp/revlv-dashboard.log"
echo "     Restart: bash ${SCRIPT_DIR}/start.sh"
echo "  ─────────────────────────────────────────────────────"
echo ""
