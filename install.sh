#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
#  Revlv CEO Dashboard — ONE-RUN INSTALLER
#
#  Sets up EVERYTHING in a single run on a fresh Mac:
#    • Xcode Command Line Tools (git/python prerequisites)
#    • Homebrew (if missing)
#    • ffmpeg            (for Telegram voice-note transcription)
#    • Google Chrome     (the dashboard opens in Chrome app mode)
#    • Python packages   (Pillow for the icon, openai-whisper for voice)
#    • Background server  as a LaunchAgent (auto-starts at login, self-heals)
#    • Desktop shortcut   with your Revlv icon
#
#  Portable: it auto-detects this Mac's username, CPU (Apple Silicon/Intel)
#  and project location, and GENERATES the LaunchAgent for this machine —
#  so the same folder installs cleanly on any Mac.
#
#  Run once from Terminal:
#    bash ~/Documents/Claude/Projects/revlv-ceo-dashboard/install.sh
#
#  Re-running is safe (idempotent). Optional: pass a logo image path as $1
#  to rebuild the app icon, e.g.  bash install.sh ~/Pictures/revlv.png
# ═══════════════════════════════════════════════════════════════════════

# Note: we do NOT use `set -e` — each step handles its own failure so a
# non-critical step (e.g. an optional package) can't abort the whole install.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
PLIST_NAME="com.revlv.ceodashboard"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
PLIST_DEST="$LAUNCH_AGENTS/$PLIST_NAME.plist"
PLIST_SRC="$PROJECT_DIR/$PLIST_NAME.plist"
APP_SRC="$PROJECT_DIR/Revlv CEO Dashboard.app"
APP_DEST="$HOME/Desktop/Revlv CEO Dashboard.app"
PORT="${REVLV_PORT:-3000}"
LOG="/tmp/revlv-dashboard.log"
LOGO_INPUT="${1:-$PROJECT_DIR/revlv-logo.png}"

say(){ printf "  %s\n" "$*"; }
hr(){  printf "  ────────────────────────────────────────────────────\n"; }

echo ""
echo "  ██████╗ ╗██╗   ██╗██╗    ██╗   CEO Dashboard"
echo "  ██╔══██╗╝██║   ██║██║    ██║   One-Run Installer"
echo "  ██████╔╝╗██║   ██║██║    ██║"
echo "  ██╔══██╗╔╚██╗ ██╔╝██║    ╚═╝"
echo "  ██║  ██║╗ ╚███╔╝  ███████╗██╗"
echo "  ╚═╝  ╚═╝╚══════╝  ╚═══╝  ╚══════╝╚═╝"
echo ""

# ── 0. Platform checks ────────────────────────────────────────
if [ "$(uname)" != "Darwin" ]; then say "❌ This installer is for macOS only."; exit 1; fi
ARCH="$(uname -m)"
if [ "$ARCH" = "arm64" ]; then BREW_PREFIX="/opt/homebrew"; else BREW_PREFIX="/usr/local"; fi
say "STEP 0 — Mac detected (${ARCH}); Homebrew prefix: ${BREW_PREFIX}"
hr

# ── 1. Xcode Command Line Tools ───────────────────────────────
say "STEP 1 — Xcode Command Line Tools"
if ! /usr/bin/xcode-select -p >/dev/null 2>&1; then
    say "⏳ Requesting Command Line Tools install (a macOS dialog may pop up)…"
    /usr/bin/xcode-select --install 2>/dev/null || true
    say "⚠️ If a dialog appeared, complete it, THEN re-run this installer."
else
    say "✅ Command Line Tools present"
fi
hr

# ── 2. Homebrew ───────────────────────────────────────────────
say "STEP 2 — Homebrew"
if ! command -v brew >/dev/null 2>&1 && [ -x "$BREW_PREFIX/bin/brew" ]; then
    eval "$("$BREW_PREFIX/bin/brew" shellenv)"
fi
if ! command -v brew >/dev/null 2>&1; then
    say "⏳ Installing Homebrew (you may be prompted for your Mac password)…"
    NONINTERACTIVE=1 /bin/bash -c \
      "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" \
      || say "⚠️ Homebrew installer reported a problem."
    [ -x "$BREW_PREFIX/bin/brew" ] && eval "$("$BREW_PREFIX/bin/brew" shellenv)"
fi
if command -v brew >/dev/null 2>&1; then say "✅ Homebrew ready"; else
    say "⚠️ Homebrew unavailable — ffmpeg/Chrome auto-install will be skipped."
fi
hr

# ── 3. ffmpeg (voice-note transcription) ──────────────────────
say "STEP 3 — ffmpeg (for Telegram voice notes)"
if command -v ffmpeg >/dev/null 2>&1; then
    say "✅ ffmpeg already installed"
elif command -v brew >/dev/null 2>&1; then
    say "⏳ Installing ffmpeg…"
    brew install ffmpeg || say "⚠️ ffmpeg install failed — voice transcription will be unavailable (everything else still works)."
else
    say "⚠️ Skipped (no Homebrew). Install later with: brew install ffmpeg"
fi
hr

# ── 4. Google Chrome (dashboard runs in Chrome app mode) ──────
say "STEP 4 — Google Chrome"
if [ -d "/Applications/Google Chrome.app" ]; then
    say "✅ Google Chrome present"
elif command -v brew >/dev/null 2>&1; then
    say "⏳ Installing Google Chrome…"
    brew install --cask google-chrome || say "⚠️ Could not auto-install Chrome — get it at https://google.com/chrome"
else
    say "⚠️ Chrome not found — install from https://google.com/chrome before launching."
fi
hr

# ── 5. Python packages ────────────────────────────────────────
say "STEP 5 — Python packages"
PYTHON="$(command -v python3 || echo /usr/bin/python3)"
say "Using: $PYTHON"
pipi(){ "$PYTHON" -m pip install --quiet --break-system-packages "$@" 2>/dev/null \
        || "$PYTHON" -m pip install --quiet --user "$@" 2>/dev/null; }
say "⏳ Pillow (app icon builder)…"
pipi Pillow && say "✅ Pillow ready" || say "⚠️ Pillow not installed — using existing icon."
say "⏳ openai-whisper (optional, large; only for voice notes)…"
if pipi openai-whisper; then say "✅ Whisper ready"; else
    say "⚠️ Whisper not installed — voice-note transcription off; the rest works fine."
fi
hr

# ── 6. Verify project files ───────────────────────────────────
say "STEP 6 — Verifying project files"
if [ ! -f "$PROJECT_DIR/index.html" ] || [ ! -f "$PROJECT_DIR/server.py" ]; then
    say "❌ index.html / server.py missing in: $PROJECT_DIR"
    exit 1
fi
say "✅ Project folder OK: $PROJECT_DIR"
hr

# ── 7. Generate the LaunchAgent for THIS machine ──────────────
say "STEP 7 — Installing background server (LaunchAgent)"
mkdir -p "$LAUNCH_AGENTS"
# Generate the plist dynamically so paths/username are correct on any Mac.
cat > "$PLIST_SRC" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON}</string>
        <string>${PROJECT_DIR}/server.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${PROJECT_DIR}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>${BREW_PREFIX}/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>REVLV_HOST</key>
        <string>127.0.0.1</string>
        <key>REVLV_PORT</key>
        <string>${PORT}</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>3</integer>
    <key>StandardOutPath</key>
    <string>${LOG}</string>
    <key>StandardErrorPath</key>
    <string>/tmp/revlv-dashboard-error.log</string>
</dict>
</plist>
PLIST
cp "$PLIST_SRC" "$PLIST_DEST"
chmod 644 "$PLIST_DEST"
say "✅ LaunchAgent generated for this Mac"
hr

# ── 8. App icon (optional) ────────────────────────────────────
say "STEP 8 — App icon"
LOGO_INPUT="$(printf '%s' "$LOGO_INPUT" | sed "s/^['\"]//;s/['\"]$//" | xargs)"
if [ -n "$LOGO_INPUT" ] && [ -f "$LOGO_INPUT" ] && "$PYTHON" -c "from PIL import Image" 2>/dev/null; then
    say "⏳ Building icon from: $LOGO_INPUT"
    LOGO_INPUT="$LOGO_INPUT" OUT_DIR="$APP_SRC/Contents/Resources" "$PYTHON" <<'PYEOF'
import os, struct, io
from PIL import Image
src=os.environ["LOGO_INPUT"]; out_dir=os.environ["OUT_DIR"]
os.makedirs(out_dir, exist_ok=True)
img=Image.open(src).convert("RGBA")
def chunk(t,b): return struct.pack(">4sI", t.encode(), 8+len(b))+b
data=b""
for t,s in [("ic07",128),("ic08",256),("ic09",512),("ic10",1024)]:
    buf=io.BytesIO(); img.resize((s,s), Image.LANCZOS).save(buf,format="PNG")
    data+=chunk(t, buf.getvalue())
open(os.path.join(out_dir,"AppIcon.icns"),"wb").write(struct.pack(">4sI", b"icns", 8+len(data))+data)
print("  ✅ Icon built")
PYEOF
else
    say "ℹ️ Skipped (no logo or Pillow) — keeping existing icon."
fi
hr

# ── 9. Start the server ───────────────────────────────────────
say "STEP 9 — Starting server on port ${PORT}"
/bin/launchctl bootout "gui/$(/usr/bin/id -u)/${PLIST_NAME}" 2>/dev/null || true
/usr/sbin/lsof -ti tcp:${PORT} 2>/dev/null | xargs /bin/kill -9 2>/dev/null || true
sleep 0.5
/bin/launchctl bootstrap "gui/$(/usr/bin/id -u)" "$PLIST_DEST" 2>/dev/null \
  || /bin/launchctl load -w "$PLIST_DEST" 2>/dev/null || true
for i in $(seq 1 20); do
    sleep 0.5
    /usr/bin/curl -sf --connect-timeout 1 "http://localhost:${PORT}/" -o /dev/null && break
done
if /usr/bin/curl -sf --connect-timeout 2 "http://localhost:${PORT}/" -o /dev/null; then
    say "✅ Server live at http://localhost:${PORT}"
else
    say "⚠️ Server not responding yet — check: cat ${LOG}"
fi
hr

# ── 10. Desktop shortcut ──────────────────────────────────────
say "STEP 10 — Desktop shortcut"
if [ -d "$APP_SRC" ]; then
    chmod +x "$APP_SRC/Contents/MacOS/RevlvCEODashboard" 2>/dev/null || true
    rm -rf "$APP_DEST"
    cp -R "$APP_SRC" "$APP_DEST"
    chmod +x "$APP_DEST/Contents/MacOS/RevlvCEODashboard" 2>/dev/null || true
    xattr -cr "$APP_DEST" 2>/dev/null || true
    touch "$APP_DEST"
    say "✅ Desktop shortcut installed → $APP_DEST"
else
    say "⚠️ App bundle missing — Desktop shortcut not installed."
fi
hr

echo ""
say "✅  ALL DONE!"
echo ""
say "▶  Double-click 'Revlv CEO Dashboard' on your Desktop to launch."
say "▶  The server auto-starts at every login and restarts on crash."
say "▶  Reach it anytime at http://localhost:${PORT} (loopback only — not exposed to your network)."
echo ""
say "Useful commands:"
say "  Status:  launchctl list | grep revlv"
say "  Logs:    cat ${LOG}"
say "  Restart: bash ${PROJECT_DIR}/start.sh"
say "  Reinstall: bash ${PROJECT_DIR}/install.sh"
echo ""
