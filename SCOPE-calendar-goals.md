# Scope: Real Calendar Events + Financial Goals Card

**For:** Revlv CEO Dashboard
**Date:** 29 May 2026
**Two features requested:**
1. Telegram "meeting" commands create **real Google Calendar events**, with the spoken date/time parsed (e.g. "meet with the software team Monday at 8am").
2. Telegram "goal" commands feed a proper **Financial Goals card** on the dashboard.

---

## Why this is a bigger build

Today the dashboard is a static page in the browser plus a small local Python server (`server.py`). It can *read* but not *write* external services:

- The calendar is a **read-only Google embed** (an iframe). The browser cannot create Google Calendar events — Google requires authenticated API calls.
- The **Financial Goals card was removed** from the layout (no `goalsList` element exists), and the `goals` data has nowhere to display.

So both features need new write paths and, for meetings, authentication with Google.

---

## Part A — Meetings → real Google Calendar events

### The core problem: a write path to Google Calendar
There are two viable ways to actually create events. They trade off setup effort vs. real-time behaviour and parsing quality.

#### Option A1 — Local server + Google Calendar API (recommended for real-time)
`server.py` gains a `/create-event` endpoint. The dashboard's existing Telegram poller detects a `meeting:` command and POSTs the text to it. The server parses the date/time and calls the Google Calendar API to insert the event.

- **Date/time parsing:** Python `dateparser` (with `search_dates`) handles "Monday at 8am", "tomorrow 3pm", "June 5 at noon", anchored to Asia/Manila and biased to future dates. The remaining words become the event title.
- **Auth:** a one-time Google OAuth setup — create a Google Cloud project, enable the Calendar API, make an OAuth Desktop client, run a one-time consent, and store a refresh token next to the server. The server refreshes the access token automatically thereafter.
- **Display:** none needed — the existing Google embed already shows the new event on its next refresh, because it's the same calendar.
- **Pros:** instant; self-contained; works exactly like the current Telegram flow.
- **Cons:** the OAuth setup is the real cost (~20–30 min of clicking through Google Cloud Console once); rule-based time parsing is good but not as flexible as an LLM on messy phrasing.

#### Option A2 — Scheduled Claude task + Calendar MCP (no OAuth, best parsing)
A scheduled task runs Claude periodically; Claude reads recent Telegram messages, understands the date/time naturally (LLM), and creates the event via the already-connected **Google Calendar MCP** (`create_event`). No Google Cloud setup at all.

- **Pros:** zero OAuth setup (reuses the Google account you already connected to Claude); far better natural-language understanding of dates/times; no new server code.
- **Cons:** **not instant** — it runs on a schedule (e.g. every few minutes), so a meeting appears after the next run, not the moment you send it; needs a small "command inbox" so the same message isn't processed twice.

### Recommendation
If "the moment I say it, it's on my calendar" matters most → **A1**. If avoiding Google Cloud setup matters most and a few-minutes delay is fine → **A2**. A1 is the better product; A2 is the lighter lift.

### Decisions needed for Part A
- A1 vs A2.
- Default meeting **duration** when only a start time is spoken (proposed: 60 minutes).
- Timezone (proposed: Asia/Manila — already used by the embed).
- Keep **auto-add with no confirmation** (consistent with today), or require a confirmation tap because calendar writes are higher-stakes?

---

## Part B — Goals → Financial Goals card

This is the lighter feature; it has no external auth.

### Work involved
1. **Re-add a Financial Goals card** to the layout (the `renderGoals()` logic, progress bars, and `addGoalModal` already exist — only the card/DOM was removed). This needs a home and a re-balance of the one-screen flex weights, since every column is height-fitted.
2. **Parse the goal from the command text.** From "goal hit ₱10M ARR by Dec" extract: target amount (₱10,000,000 — handle `₱`, `M`/`K`, commas), an optional deadline, and the name (remaining text). First monetary value = target; default category if none stated.
3. **Wire the Telegram `goal:` command** to push into the `goals` array and `renderGoals()` instead of the To-Do list.

### Decisions needed for Part B
- **Placement:** which column gets the Goals card? Options: right column (below Operations + To-Do — tightest), left column (below Calendar), or replace one existing card. Adding a 4th/3rd card shrinks its neighbours.
- Should goals also persist to a `data/goals.json` file (so a future sync/report can read them), or stay in browser storage only as today?

---

## Dependencies / installs (Mac, one-time)

- **A1 only:** `pip install --user google-api-python-client google-auth google-auth-oauthlib dateparser` for `/usr/bin/python3`, plus the one-time Google OAuth consent.
- **A2 only:** none (uses the existing Calendar MCP) — just create the scheduled task.
- **Part B:** none.

---

## Effort estimate (rough)

| Piece | Effort | External setup |
|---|---|---|
| A1 — server + Google API + dateparser | Medium–High | Google Cloud OAuth (one-time) |
| A2 — scheduled Claude task + Calendar MCP | Low–Medium | none |
| B — Goals card + parsing | Low–Medium | none |

---

## Risks / notes
- **OAuth token security (A1):** the refresh token sits on your Mac next to the server. Local-only, but worth knowing.
- **Date parsing edge cases:** "next Thursday", "EOD", "in 2 weeks" — A2 (LLM) handles these; A1 (dateparser) handles most but can miss unusual phrasing. We can fall back to a To-Do (as today) when parsing is uncertain.
- **Layout pressure (B):** the dashboard already fits one screen exactly; adding the Goals card means shrinking something. We'll pick the least-disruptive spot.
- **Duplicate handling (A2):** needs a processed-message marker so a meeting isn't created twice across runs.

---

## Suggested order
1. **Part B (Goals card)** first — quick, self-contained, no auth, immediate visible value.
2. **Part A (meetings)** second — pick A1 or A2; if A1, do the Google OAuth setup, then the endpoint + parsing.
