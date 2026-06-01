# REVLV CEO Dashboard — Setup Guide

**Owner:** Ryan Labrador, CEO — Revlv Solutions Inc.
*Tomorrow's Solutions. Now.*

---

## WHAT THIS DASHBOARD DOES

A personal CEO command center that lives entirely on your Mac. It shows your Facebook Messenger and Google Chat, Google Calendar, fitness, financial goals, to-do list, daily Gospel, weather, focus timer, Telegram bot, and company culture — all behind a password-protected login. No cloud accounts needed beyond what Claude already connects to.

---

## FIRST-TIME SETUP

### Step 1 — Run the One-Run Installer (Once Only)

Put the project folder at `~/Documents/Claude/Projects/revlv-ceo-dashboard`, open Terminal, and run:
```bash
bash ~/Documents/Claude/Projects/revlv-ceo-dashboard/install.sh
```

`install.sh` sets up **everything in a single run**, and is safe to re-run:
- Installs **Xcode Command Line Tools**, **Homebrew**, **ffmpeg** (voice notes), and **Google Chrome** if any are missing
- Installs the Python packages **Pillow** (app icon) and **openai-whisper** (voice transcription — optional/large; the dashboard works without it)
- **Generates the background server (LaunchAgent) for this specific Mac** — it auto-detects your username, CPU (Apple Silicon/Intel) and folder location, so there are no hard-coded paths
- Builds the app icon from `revlv-logo.png` (or pass your own: `bash install.sh ~/Pictures/mylogo.png`)
- Starts the server on port 3000 (bound to **localhost only** — never exposed to your network) and installs the **Revlv CEO Dashboard** Desktop shortcut

> `setup.sh` still works too — it now simply forwards to `install.sh`.

You only need to run this once per Mac. After that, the server starts automatically at every login.

**Heads-up during install:** Homebrew may ask for your Mac password, and the very first run may pop a macOS dialog to install Command Line Tools — finish that dialog, then re-run `install.sh`.

---

### Step 2 — Create Your Admin Account

On the very first launch, the dashboard will ask you to create your admin username and password. This is your only account — no additional accounts can be created. Your password encrypts all settings and API keys in an AES-256 vault stored locally.

**After account creation, the setup wizard walks you through the remaining configuration steps. You only see it once.**

On every subsequent launch, you go straight to the login screen.

---

### Step 3 — Daily Launch

Double-click **Revlv CEO Dashboard** on your Desktop. This opens the dashboard in full-screen Chrome and always shows the login screen first — no one can access your dashboard without your password.

**Alternative:** Open Terminal and run:
```bash
bash ~/Documents/Claude/Projects/revlv-ceo-dashboard/start.sh
```

---

### Step 4 — Google Calendar (Claude MCP Connector) + Chat Widgets

Google Calendar is connected via **Claude's built-in MCP connector** — no API keys, no Google Cloud Console, no OAuth setup required.

**How it works:**
- A scheduled task syncs your Google Calendar and writes it to `data/calendar.json`
- A second task runs at **5:00 AM** daily for the daily Gospel readings
- The dashboard reads those local files on a timer — no browser API needed

**Messenger & Google Chat widgets:**
These two chat services block being embedded in a frame, so each widget is a quick-launch card. Click **Open Messenger** or **Open Google Chat** to open the service in a focused popup window (signed in as your normal browser session). Both widgets are fully movable (drag in layout-edit mode) and can be hidden/restored like any other widget. You can change the URLs they open via `CFG.messengerUrl` / `CFG.chatUrl`.

---

### Step 5 — Weather API (Free)

1. Go to https://openweathermap.org/api
2. Create a free account
3. Copy your API key
4. Open Settings on the dashboard (requires your password)
5. Go to the Weather section → paste the key and set your city to: `Makati City,PH`

---

### Step 6 — Telegram Bot Setup

1. Open Telegram → search for **@BotFather**
2. Send: `/newbot`
3. Follow prompts, choose a name (e.g. "RevlvCEO Bot")
4. Copy the bot token BotFather gives you
5. **Get your Chat ID:**
   - Message your new bot once (any text)
   - Visit: `https://api.telegram.org/bot[YOUR_TOKEN]/getUpdates`
   - Find `"chat":{"id":XXXXXXX}` — that number is your Chat ID
6. Open Settings on the dashboard → Telegram section → paste both values

**Telegram dictation commands** (work as a typed message **or** a voice note):

| Command words | Action |
|---------------|--------|
| `task:` · `todo:` · `do:` | Adds a high-priority item to the To-Do list |
| `reminder:` · `remind:` | Adds a reminder to the To-Do list |
| `meeting:` · `event:` · `sched:` · `schedule:` | Creates a Google Calendar event (date/time parsed) |
| `goal:` · `target:` | Adds a Financial Goal (amount parsed if present) |
| `note:` · `memo:` · `log:` | Saves a note in the Telegram panel |

- The Telegram Dictations widget **shows this command list by default**, until your first dictation arrives.
- Text example: `task: Call John re: partnership proposal`
- 🎙️ **Voice notes** are transcribed locally on your Mac (Whisper). Just say the command word first — e.g. *"task, meet the software team Monday 8am."* Natural lead-ins also work (*"add a task…"*, *"new reminder…"*, *"please schedule a meeting…"*). Anything without a command word is saved as a note.
- The colon is optional for voice (`task call John` works); for typed messages use `task:` or the Telegram slash form `/task`.

---

### Step 7 — Logo Upload

Open Settings → Step 5 (Culture) → scroll to **Dashboard Logo** → upload your PNG or SVG logo. It replaces the placeholder in the header and login screen. Stored encrypted in your local vault.

---

### Step 8 — Messenger & Google Chat Widgets

There is nothing to configure. The two widgets open Facebook Messenger (`https://www.messenger.com/`) and Google Chat (`https://mail.google.com/chat/u/0/`) in popup windows using your existing browser sessions. To point a widget at a different URL or workspace, change `CFG.messengerUrl` / `CFG.chatUrl` in Settings/config.

- **Move** a widget: click the ⠿ layout button in the header, then drag.
- **Hide / restore** a widget: use the ✕ on the card or the 📦 restore button in the header.

---

## DASHBOARD FEATURES

| Feature | Status | Notes |
|---------|--------|-------|
| Login + Password Protection | ✅ | AES-256 encrypted vault |
| Setup Wizard (First Run Only) | ✅ | Shows once; skipped on all future logins |
| Desktop Shortcut (Full-screen) | ✅ | Always forces login screen |
| Background Server (LaunchAgent) | ✅ | Auto-starts at login, auto-restarts on crash |
| Facebook Messenger Widget | ✅ | Launch card — opens Messenger in a popup window |
| Google Chat Widget | ✅ | Launch card — opens Google Chat in a popup window |
| Google Calendar | ✅ | Today's schedule, auto-refresh |
| Daily Gospel Readings | ✅ | Full text in widget, USCCB source |
| Gospel — Daily MCP Sync | ✅ | Scheduled 5:00 AM daily |
| To-Do List | ✅ | Priority levels, local storage |
| Financial Goals | ✅ | Progress bars, ₱ amounts |
| Fitness Tracker | ✅ | Manual logging (steps/cal/water/sleep) |
| Weather + AI Briefing | ✅ | OpenWeatherMap API |
| Focus / Pomodoro Timer | ✅ | 25 / 50 / 90 min modes |
| Telegram Dictation | ✅ | Text + voice commands; command legend shown by default; polls for new messages |
| Team Pulse | ✅ | Demo data (connect internal APIs) |
| Culture Banner | ✅ | Mission + rotating daily values |
| Leadership HQ Panel | ✅ | Goals, HBS Compass, Unit 2, Principles |
| Document Uploads | ✅ | PDF, PPTX, DOCX — stored in vault |
| Timezone Clocks | ✅ | Manila 🇵🇭, Boston 🇺🇸, Helsinki 🇫🇮 |
| Dark / Light Mode | ✅ | Toggle in header |
| Custom Logo Upload | ✅ | PNG/SVG, stored encrypted |
| All Actions Need Approval | ✅ | Confirm modal for every action |

---

## SCHEDULED TASKS (Auto-run in Claude/Cowork)

| Task ID | Schedule | What it does |
|---------|----------|--------------|
| `revlv-ceo-gospel-sync` | 5:00 AM daily | Fetches USCCB readings → writes `data/gospel.json` |
| `revlv-calendar-sync` | every 2 hours | Fetches Google Calendar via MCP → writes `data/calendar.json` |
| `revlv-meeting-creator` | every 5 min | Turns Telegram `meeting:` commands into real Google Calendar events |

Manage these in the **Scheduled** panel in the Claude sidebar. Run them manually anytime to refresh.

> The old Gmail tasks (`revlv-ceo-gmail-sync`, `revlv-gmail-frequent-sync`, `revlv-outbox-sender`) are **disabled** — Gmail was removed from the dashboard. Delete them from the Scheduled panel if you want them gone for good. They are not recreated by the installer.

---

## FILE STRUCTURE

```
revlv-ceo-dashboard/
├── index.html                       ← Main dashboard (single file)
├── server.py                        ← Local server (serves files + /transcribe voice endpoint; localhost-only)
├── install.sh                       ← ★ Run once: installs ALL dependencies + server + shortcut
├── setup.sh                         ← Compatibility wrapper → forwards to install.sh
├── start.sh                         ← Manual restart + open dashboard in Chrome
├── com.revlv.ceodashboard.plist      ← LaunchAgent (regenerated per-Mac by install.sh)
├── revlv-logo.png                   ← Source logo for the app icon
├── Revlv CEO Dashboard.app/         ← Desktop shortcut (macOS .app bundle)
│   └── Contents/
│       ├── Info.plist
│       ├── MacOS/RevlvCEODashboard  ← Shell launcher script ($HOME-relative)
│       └── Resources/AppIcon.icns  ← App icon (built from revlv-logo.png by install.sh)
├── data/
│   ├── calendar.json                ← Calendar events (written by Claude MCP)
│   ├── gospel.json                  ← Daily Gospel readings (written by Claude MCP)
│   └── meetings-queue.json          ← Pending Telegram meeting commands
├── backups/                         ← Your exported data backups (.json) — keep private
└── prompt/
    └── dashboard-prompt.md          ← This file
```

---

## MOVE / RE-INSTALL ON ANOTHER MAC

Everything is portable — there are no hard-coded usernames or paths (the installer generates the LaunchAgent for each machine).

1. **Copy the whole `revlv-ceo-dashboard` folder** to the new Mac at `~/Documents/Claude/Projects/revlv-ceo-dashboard` (AirDrop, USB, or git — your choice).
2. Open Terminal and run:
   ```bash
   bash ~/Documents/Claude/Projects/revlv-ceo-dashboard/install.sh
   ```
   It installs Homebrew/ffmpeg/Chrome/Python packages as needed, generates the server for that Mac, and puts the shortcut on the Desktop.
3. **Bring your data across** (optional but recommended): on the old Mac, open Settings → Other Settings → **Export All Data**. On the new Mac, after first launch, create the admin account, then Settings → **Restore from Backup** and pick that file. Your vault, to-dos, goals, widgets, and layout all come over.
4. **Re-create the scheduled tasks** (Calendar/Gospel/Meeting-creator) on the new Mac by asking Claude in Cowork to set them up, or copy them from the **Scheduled** panel — these live in Claude, not in the project folder.

---

## GITHUB BACKUP & VERSION RESTORE

Settings → Other Settings → **🐙 GitHub Backup & Version History** lets you push the whole dashboard (code **and** settings, including the encrypted vault) to a GitHub repo and roll back to any earlier version.

**One-time setup:**
1. On GitHub, create a **PRIVATE** repository (an empty repo, no README, works best for the first push).
2. Create a Personal Access Token with the **`repo`** scope (GitHub → Settings → Developer settings → Personal access tokens).
3. In the dashboard (now under the **⚙️ Settings** tab): paste the token and click **🔗 Connect** — it verifies the token against GitHub, shows who you're signed in as, and auto-fills your username/email plus a dropdown of your repos. (GitHub has no "Sign in with Google", so a token is how the app connects.) Pick your repo, set the branch, then **💾 Save Settings** (stored in your encrypted vault).

**Usage:**
- **⬆️ Push to GitHub** — mirrors your full state to `backups/dashboard-state.json` and commits + pushes the entire project. Confirm the warning first.
- **📜 View / Restore Versions** — lists recent commits; click **↩️ Restore** on any to roll the code back to that version (your live data/vault is untouched; the page reloads). The next push moves history forward, so no force-push is needed.

**How it works / security:**
- The push/restore run through the **local server** (`/git-push`, `/git-log`, `/git-restore` — localhost-only, origin-checked). The browser can't run git directly.
- The token is sent only to your Mac's own server and used via an Authorization header — never written to disk, git config, or logs.
- ⚠️ The backup includes your **encrypted vault and credentials**. **Only ever use a private repo.** The vault stays AES-encrypted in the committed file.
- Requires `git` (installed by `install.sh` via Xcode Command Line Tools).
- `.gitignore` keeps local `.zip` snapshots and caches out of the repo but **does** include `backups/dashboard-state.json` so your settings travel with the code.

---

## SECURITY NOTES

- All API keys and config are stored in an **AES-256-GCM encrypted vault** in your browser's localStorage — never sent to any server
- The vault is unlocked only with your admin password
- The setup wizard appears only on the very first login after account creation; all subsequent logins go straight to the main dashboard
- The Desktop shortcut always clears the session on launch (`?fresh=1`) — no one can open the dashboard without the password
- Only one admin account is permitted — no additional accounts can be created
- Your Calendar data lives only on your Mac — not in the cloud
- The local server binds to **127.0.0.1 only** (not your network) and rejects cross-origin POST requests
- **Back up your data:** Settings → Other Settings → **Export All Data** writes a single JSON (vault + all widgets/data). Keep it private — it contains your encrypted vault and credentials. Restore it via **Restore from Backup**.

---

## SERVER MANAGEMENT

The background server runs as a macOS LaunchAgent and manages itself automatically.

| Action | Command |
|--------|---------|
| Check server status | `launchctl list \| grep revlv` |
| View server logs | `cat /tmp/revlv-dashboard.log` |
| Stop server | `launchctl unload ~/Library/LaunchAgents/com.revlv.ceodashboard.plist` |
| Start server | `launchctl load ~/Library/LaunchAgents/com.revlv.ceodashboard.plist` |
| Open dashboard manually | `bash ~/Documents/Claude/Projects/revlv-ceo-dashboard/start.sh` |
| Re-run / repair install | `bash ~/Documents/Claude/Projects/revlv-ceo-dashboard/install.sh` |

---

## SUGGESTED FUTURE FEATURES

1. **Unread badges on chat widgets** — Surface Messenger / Google Chat unread counts on the launch cards
2. **Zoom/Meet integration** — Join calls directly from calendar events
3. **Revlv internal systems API** — Connect HR, billing, NOC monitoring
4. **Investment portfolio tracker** — Real-time stock/crypto prices
5. **Family wealth dashboard sub-panel** — Separate view for generational wealth planning
6. **Voice command** — Use browser's Web Speech API to dictate directly to the dashboard
7. **Team performance KPIs** — Revenue, project status, NOC uptime
8. **CRM mini-panel** — Quick view of top client relationships
9. **Automated weekly CEO report** — Summarizes the week's tasks and progress
