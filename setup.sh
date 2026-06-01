#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
#  Revlv CEO Dashboard — Setup (compatibility wrapper)
#
#  Everything now lives in the single one-run installer, install.sh, which
#  also installs dependencies (Homebrew, ffmpeg, Chrome, Python packages)
#  and generates the LaunchAgent for THIS Mac.
#
#  This wrapper just forwards to it so older instructions keep working.
#    bash ~/Documents/Claude/Projects/revlv-ceo-dashboard/setup.sh
# ═══════════════════════════════════════════════════════════════════════
exec bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/install.sh" "$@"
