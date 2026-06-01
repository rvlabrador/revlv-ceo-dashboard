#!/bin/bash
# Run this once to place the dashboard shortcut on your Desktop.
APP_SRC="$(cd "$(dirname "$0")" && pwd)/Revlv CEO Dashboard.app"
DESKTOP="$HOME/Desktop"
DEST="$DESKTOP/Revlv CEO Dashboard.app"

echo "Installing Revlv CEO Dashboard shortcut..."
rm -rf "$DEST"
cp -r "$APP_SRC" "$DEST"
chmod +x "$DEST/Contents/MacOS/RevlvCEODashboard"

# Clear macOS quarantine flag (allows double-click without Gatekeeper warning)
xattr -cr "$DEST" 2>/dev/null

echo "✅ Shortcut installed on Desktop!"
echo "   Double-click 'Revlv CEO Dashboard' on your Desktop to launch."
