#!/usr/bin/env python3
"""
Revlv CEO Dashboard — local server.

Serves the dashboard's static files (like `python -m http.server`) AND adds a
local speech-to-text endpoint:

    POST /transcribe
        Content-Type: application/json   body = {"token": "<bot token>", "file_id": "<voice file id>"}
            → the server downloads the voice clip from Telegram itself (no browser
              CORS issues) and transcribes it.
        Content-Type: audio/*            body = raw audio bytes
            → transcribes the posted bytes directly.
        Response: {"text": "..."} on success, {"error": "..."} on failure.

Transcription runs LOCALLY via the `openai-whisper` package — no API key, no
external transcription service.

Setup on the Mac (one time):
    /usr/bin/python3 -m pip install --user -U openai-whisper
    brew install ffmpeg            # Whisper needs ffmpeg to decode audio

Optional environment variables:
    REVLV_PORT            (default 3000)
    REVLV_WHISPER_MODEL   tiny | base | small | medium | large   (default "base")
"""

import os
import re
import sys
import json
import uuid
import shutil
import base64
import datetime
import tempfile
import subprocess
import urllib.parse
import urllib.request
import http.server
import socketserver

PORT = int(os.environ.get("REVLV_PORT", "3000"))
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
WHISPER_MODEL = os.environ.get("REVLV_WHISPER_MODEL", "base")
# Force the transcription language so accented English isn't mis-detected as another
# language. Override with REVLV_WHISPER_LANG (e.g. "tl" for Filipino, or "" to auto-detect).
WHISPER_LANG = os.environ.get("REVLV_WHISPER_LANG", "en")

# Only the dashboard's own local origins may call the POST endpoints / read CORS
# responses. This blocks a malicious website (visited while the server runs) from
# POSTing to the local API or reading responses cross-origin (CSRF / data exfil).
LOCAL_ORIGINS = {
    f"http://localhost:{PORT}",
    f"http://127.0.0.1:{PORT}",
}

# Whisper shells out to `ffmpeg` to decode audio. When this server is launched by
# a macOS LaunchAgent it gets a minimal PATH that excludes Homebrew/MacPorts dirs,
# so ffmpeg (installed via `brew install ffmpeg`) isn't found. Make sure those
# directories are on PATH regardless of how the server was started.
_EXTRA_BIN = ["/opt/homebrew/bin", "/usr/local/bin", "/opt/local/bin"]
_cur_path = os.environ.get("PATH", "")
os.environ["PATH"] = os.pathsep.join(
    [p for p in _EXTRA_BIN if p not in _cur_path.split(os.pathsep)] +
    ([_cur_path] if _cur_path else [])
)

# Lazily-loaded Whisper model (kept warm between requests).
_model = None


def get_model():
    """Load the Whisper model on first use. Raises ModuleNotFoundError if the
    `openai-whisper` package is not installed."""
    global _model
    if _model is None:
        import whisper  # provided by the `openai-whisper` pip package
        sys.stderr.write(f"[whisper] loading model '{WHISPER_MODEL}'...\n")
        _model = whisper.load_model(WHISPER_MODEL)
        sys.stderr.write("[whisper] model ready\n")
    return _model


def _http_get(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": "Revlv-Dashboard/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def tg_download(token, file_id):
    """Download a Telegram file server-side. Returns (bytes, file_path)."""
    meta_raw = _http_get(
        f"https://api.telegram.org/bot{token}/getFile?file_id={urllib.parse.quote(file_id)}", 30)
    meta = json.loads(meta_raw.decode("utf-8"))
    if not meta.get("ok") or not meta.get("result", {}).get("file_path"):
        raise RuntimeError("Telegram getFile failed: " + json.dumps(meta.get("description", "unknown")))
    fpath = meta["result"]["file_path"]
    data = _http_get(f"https://api.telegram.org/file/bot{token}/{fpath}", 120)
    return data, fpath


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    # Never let the browser cache the dashboard — avoids stale-page issues.
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def _origin_allowed(self):
        # Same-origin fetches often omit Origin; only reject when a *foreign* Origin is present.
        origin = self.headers.get("Origin")
        return (origin is None) or (origin in LOCAL_ORIGINS)

    def _cors_origin_header(self):
        origin = self.headers.get("Origin")
        if origin in LOCAL_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

    def _send_json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors_origin_header()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_origin_header()
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _handle_queue_meeting(self):
        """Append a meeting command to data/meetings-queue.json for the scheduled
        Claude task to turn into a real Google Calendar event."""
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            payload = json.loads(raw.decode("utf-8") or "{}")
            text = (payload.get("text") or "").strip()
            if not text:
                self._send_json(400, {"error": "Missing text"})
                return
            qpath = os.path.join(DIRECTORY, "data", "meetings-queue.json")
            os.makedirs(os.path.dirname(qpath), exist_ok=True)
            queue = {"pending": []}
            if os.path.exists(qpath):
                try:
                    with open(qpath, "r", encoding="utf-8") as f:
                        queue = json.load(f)
                except Exception:
                    queue = {"pending": []}
            if not isinstance(queue.get("pending"), list):
                queue["pending"] = []
            queue["pending"].append({
                "id": uuid.uuid4().hex[:12],
                "text": text,
                "receivedAt": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "status": "pending",
            })
            with open(qpath, "w", encoding="utf-8") as f:
                json.dump(queue, f, indent=2, ensure_ascii=False)
            self._send_json(200, {"ok": True, "queued": text})
        except Exception as e:  # noqa: BLE001
            self._send_json(500, {"error": str(e)})

    # ── GitHub backup / restore helpers ──────────────────────────
    def _json_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    @staticmethod
    def _git_slug(remote):
        """Accept 'owner/repo' or a full github URL; return 'owner/repo' or None."""
        remote = (remote or "").strip()
        m = re.match(r'^https?://github\.com/([^/]+/[^/]+?)(?:\.git)?/?$', remote)
        if m:
            return m.group(1)
        if re.match(r'^[\w.-]+/[\w.-]+$', remote):
            return remote
        return None

    def _git(self, args, token=None, timeout=120):
        """Run a git command in the project dir; scrub the token from any output."""
        res = subprocess.run(["git"] + args, cwd=DIRECTORY, capture_output=True,
                             text=True, timeout=timeout,
                             env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
        out = ((res.stdout or "") + (res.stderr or ""))
        if token:
            out = out.replace(token, "***")
        return res.returncode, out.strip()

    @staticmethod
    def _git_auth_header(token):
        # Pass the PAT via an Authorization header (never in the URL, git config, or disk).
        return "http.extraheader=AUTHORIZATION: basic " + \
            base64.b64encode(("x-access-token:" + token).encode()).decode()

    def _handle_save_backup(self):
        """Persist the dashboard's full localStorage export (settings vault + all data)
        into backups/dashboard-state.json so it can be committed to git."""
        try:
            data = self._json_body()
            if not isinstance(data, dict):
                self._send_json(400, {"error": "Expected a JSON object"})
                return
            bdir = os.path.join(DIRECTORY, "backups")
            os.makedirs(bdir, exist_ok=True)
            with open(os.path.join(bdir, "dashboard-state.json"), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._send_json(200, {"ok": True, "path": "backups/dashboard-state.json",
                                  "keys": len(data.get("data", {}) or {})})
        except Exception as e:  # noqa: BLE001
            self._send_json(500, {"error": str(e)})

    def _handle_git_push(self):
        """Commit the whole project and push to the user's GitHub repo using a PAT."""
        try:
            p = self._json_body()
            slug = self._git_slug(p.get("remote"))
            token = (p.get("token") or "").strip()
            branch = (p.get("branch") or "main").strip() or "main"
            name = (p.get("name") or "Revlv Dashboard").strip()
            email = (p.get("email") or "dashboard@revlv.local").strip()
            msg = (p.get("message") or ("Dashboard backup " +
                   datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))).strip()
            if not slug or not token:
                self._send_json(400, {"error": "Repository (owner/repo) and token are required"})
                return
            if not shutil.which("git"):
                self._send_json(501, {"error": "git not found — run install.sh"})
                return
            url = f"https://github.com/{slug}.git"
            hdr = self._git_auth_header(token)
            steps = []

            def do(label, args, timeout=120):
                rc, out = self._git(args, token=token, timeout=timeout)
                steps.append({"step": label, "code": rc, "out": out[-400:]})
                return rc

            if not os.path.isdir(os.path.join(DIRECTORY, ".git")):
                do("init", ["init", "-q"])
            self._git(["config", "user.name", name])
            self._git(["config", "user.email", email])
            do("branch", ["checkout", "-q", "-B", branch])
            do("add", ["add", "-A"])
            do("commit", ["commit", "-q", "-m", msg])  # nonzero if nothing changed — OK
            rc = do("push", ["-c", hdr, "push", url, "HEAD:" + branch], timeout=180)
            self._send_json(200 if rc == 0 else 500,
                            {"ok": rc == 0, "repo": slug, "branch": branch, "steps": steps})
        except subprocess.TimeoutExpired:
            self._send_json(504, {"error": "git operation timed out"})
        except Exception as e:  # noqa: BLE001
            self._send_json(500, {"error": str(e)})

    def _handle_git_log(self):
        """List recent versions (commits) on the repo branch so the user can pick one."""
        try:
            p = self._json_body()
            slug = self._git_slug(p.get("remote"))
            token = (p.get("token") or "").strip()
            branch = (p.get("branch") or "main").strip() or "main"
            if not slug or not token:
                self._send_json(400, {"error": "Repository and token are required"})
                return
            if not shutil.which("git"):
                self._send_json(501, {"error": "git not found — run install.sh"})
                return
            url = f"https://github.com/{slug}.git"
            hdr = self._git_auth_header(token)
            if not os.path.isdir(os.path.join(DIRECTORY, ".git")):
                self._git(["init", "-q"])
            rc, out = self._git(["-c", hdr, "fetch", "--depth", "50", url, branch], token=token, timeout=120)
            if rc != 0:
                self._send_json(500, {"error": "Could not fetch from GitHub", "detail": out[-400:]})
                return
            rc, out = self._git(["log", "--max-count=40", "--date=format:%Y-%m-%d %H:%M",
                                 "--pretty=%H%x1f%cd%x1f%s", "FETCH_HEAD"])
            versions = []
            for line in out.splitlines():
                parts = line.split("\x1f")
                if len(parts) == 3:
                    versions.append({"sha": parts[0], "short": parts[0][:8],
                                     "date": parts[1], "subject": parts[2]})
            self._send_json(200, {"ok": True, "repo": slug, "branch": branch, "versions": versions})
        except Exception as e:  # noqa: BLE001
            self._send_json(500, {"error": str(e)})

    def _handle_git_restore(self):
        """Restore the working files to a chosen commit (HEAD stays, so the next push
        moves history forward — no force-push needed)."""
        try:
            p = self._json_body()
            slug = self._git_slug(p.get("remote"))
            token = (p.get("token") or "").strip()
            branch = (p.get("branch") or "main").strip() or "main"
            sha = (p.get("sha") or "").strip()
            if not slug or not token or not re.match(r'^[0-9a-fA-F]{7,40}$', sha):
                self._send_json(400, {"error": "Repository, token and a valid commit SHA are required"})
                return
            if not shutil.which("git"):
                self._send_json(501, {"error": "git not found — run install.sh"})
                return
            url = f"https://github.com/{slug}.git"
            hdr = self._git_auth_header(token)
            if not os.path.isdir(os.path.join(DIRECTORY, ".git")):
                self._git(["init", "-q"])
            # Fetch full branch history so the target commit object is available locally.
            self._git(["-c", hdr, "fetch", url, branch], token=token, timeout=150)
            rc, out = self._git(["checkout", sha, "--", "."], token=token, timeout=120)
            self._send_json(200 if rc == 0 else 500,
                            {"ok": rc == 0, "sha": sha, "detail": out[-400:]})
        except Exception as e:  # noqa: BLE001
            self._send_json(500, {"error": str(e)})

    def _tg_call(self, token, method, query=""):
        """Call a Telegram Bot API method server-side and return parsed JSON."""
        url = f"https://api.telegram.org/bot{token}/{method}"
        if query:
            url += "?" + query
        raw = _http_get(url, 25)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {"ok": False, "error": "invalid response from Telegram"}

    def _handle_telegram_updates(self):
        """Proxy Telegram getUpdates server-side so the browser never has to call
        api.telegram.org directly (avoids CORS / network blocking). The bot token is
        used only for these outbound calls.

        Supports {"action":"diag"} which returns getMe + getWebhookInfo so the
        dashboard can tell the user exactly what's wrong (bad token, webhook set, etc.).
        Also auto-removes a webhook when getUpdates is blocked by a 409 conflict, which
        is the most common reason a bot 'never connects'."""
        try:
            p = self._json_body()
            token = (p.get("token") or "").strip()
            action = (p.get("action") or "").strip()
            if not token:
                self._send_json(400, {"ok": False, "error": "missing token"})
                return

            if action == "diag":
                me = self._tg_call(token, "getMe")
                wh = self._tg_call(token, "getWebhookInfo")
                self._send_json(200, {"ok": bool(me.get("ok")), "getMe": me, "webhook": wh})
                return

            try:
                offset = int(p.get("offset") or 0)
            except Exception:
                offset = 0
            data = self._tg_call(token, "getUpdates", f"offset={offset}&limit=20&timeout=0")

            # A webhook makes getUpdates fail with 409 forever — auto-clear it and retry once.
            desc = str(data.get("description", "")).lower()
            if (not data.get("ok")) and (data.get("error_code") == 409 or "webhook" in desc):
                self._tg_call(token, "deleteWebhook", "drop_pending_updates=false")
                data = self._tg_call(token, "getUpdates", f"offset={offset}&limit=20&timeout=0")
                data["_webhookCleared"] = True

            self._send_json(200, data)
        except Exception as e:  # noqa: BLE001
            self._send_json(502, {"ok": False, "error": str(e)})

    def do_POST(self):
        # CSRF / cross-origin guard: reject POSTs that carry a non-local Origin header.
        if not self._origin_allowed():
            self._send_json(403, {"error": "Forbidden: cross-origin request rejected"})
            return
        route = self.path.split("?")[0]
        if route == "/queue-meeting":
            self._handle_queue_meeting()
            return
        if route == "/telegram":
            self._handle_telegram_updates()
            return
        if route == "/save-backup":
            self._handle_save_backup()
            return
        if route == "/git-push":
            self._handle_git_push()
            return
        if route == "/git-log":
            self._handle_git_log()
            return
        if route == "/git-restore":
            self._handle_git_restore()
            return
        if route != "/transcribe":
            self._send_json(404, {"error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b""
            ct = (self.headers.get("Content-Type") or "").lower()

            audio_bytes = None
            suffix = ".ogg"

            # Auto-detect a JSON {token, file_id} payload regardless of Content-Type,
            # so a header mismatch can't cause the JSON to be written as "audio".
            payload = None
            if raw[:1] in (b"{", b"[") or "application/json" in ct:
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except Exception:
                    payload = None

            if isinstance(payload, dict) and payload.get("file_id"):
                # Browser sent {token, file_id} — download the audio here (no CORS).
                token = payload.get("token")
                file_id = payload.get("file_id")
                if not token:
                    self._send_json(400, {"error": "Missing Telegram token"})
                    return
                audio_bytes, fpath = tg_download(token, file_id)
                ext = os.path.splitext(fpath)[1]
                if ext:
                    suffix = ext
            else:
                # Raw audio bytes posted directly.
                audio_bytes = raw
                if "wav" in ct:
                    suffix = ".wav"
                elif "mp3" in ct or "mpeg" in ct:
                    suffix = ".mp3"
                elif "m4a" in ct or "mp4" in ct or "aac" in ct:
                    suffix = ".m4a"
                elif "webm" in ct:
                    suffix = ".webm"

            # Guard against an empty / non-audio body (this is what produces ffmpeg's
            # "End of file" error) and report it clearly.
            if not audio_bytes or len(audio_bytes) < 64:
                self._send_json(400, {
                    "error": f"Audio was empty or too small ({len(audio_bytes) if audio_bytes else 0} bytes). "
                             "Make sure the server was restarted (start.sh) and the page hard-reloaded."
                })
                return
            sys.stderr.write(f"[transcribe] received {len(audio_bytes)} bytes (suffix {suffix})\n")

            # Whisper needs ffmpeg to decode audio — fail with a clear message if absent.
            if shutil.which("ffmpeg") is None:
                self._send_json(501, {
                    "error": "ffmpeg not found. Install it then re-run start.sh:  brew install ffmpeg"
                })
                return

            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tf:
                tf.write(audio_bytes)
                tmp_path = tf.name
            try:
                model = get_model()
                _opts = {"fp16": False}
                if WHISPER_LANG:
                    _opts["language"] = WHISPER_LANG  # force language (default: English)
                result = model.transcribe(tmp_path, **_opts)
                self._send_json(200, {"text": (result.get("text") or "").strip()})
            finally:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
        except ModuleNotFoundError:
            self._send_json(501, {
                "error": "Local Whisper is not installed for this Python. Run:  /usr/bin/python3 -m pip install --user -U openai-whisper   (and: brew install ffmpeg)"
            })
        except Exception as e:  # noqa: BLE001 — surface any failure to the UI
            self._send_json(500, {"error": str(e)})

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    # Bind to loopback only so the dashboard and its data files are never reachable
    # from other devices on the network (override with REVLV_HOST if you really need to).
    host = os.environ.get("REVLV_HOST", "127.0.0.1")
    httpd = ThreadingHTTPServer((host, PORT), Handler)
    sys.stderr.write(
        f"Revlv dashboard server on http://{host}:{PORT}  "
        f"(local Whisper model: {WHISPER_MODEL})\n"
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
