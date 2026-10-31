"""A tiny helper the examples share: your key from the environment (or starter/.env), and one GET.
Standard library only."""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("TILLA_API_BASE", "https://api.tillacrypto.com")
HEADERS = {"User-Agent": "tilla-examples/1.0"}


def key():
    k = os.environ.get("TILLA_API_KEY", "").strip()
    if not k:
        env = os.path.join(os.path.dirname(__file__), "..", "starter", ".env")
        if os.path.exists(env):
            for line in open(env, encoding="utf-8"):
                if line.startswith("TILLA_API_KEY="):
                    k = line.split("=", 1)[1].strip()
    if not k:
        raise SystemExit("No key. Get a free one:\n"
                         "  curl -X POST https://api.tillacrypto.com/v1/demo_key\n"
                         "then:  set TILLA_API_KEY=tk_live_...   (macOS/Linux: export TILLA_API_KEY=...)")
    return k


def get(path, **params):
    q = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    url = BASE + path + ("?" + q if q else "")
    req = urllib.request.Request(url, headers={**HEADERS, "X-API-Key": key()})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:      # the API says why in plain words - show that, not a traceback
        body = e.read().decode("utf-8", "replace")
        try:
            body = json.loads(body).get("error", body)
        except ValueError:
            pass
        raise SystemExit(f"HTTP {e.code}: {body}")


def tier():
    return get("/v1/usage")["tier"]
