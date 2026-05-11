"""Lightweight web UI for managing custom v2rayN routing-rule domains.

Run: `python app.py`  →  http://127.0.0.1:8765
"""

import importlib.util
import json
import os
import subprocess
import threading
from pathlib import Path

from flask import Flask, jsonify, render_template, request

ROOT = Path(__file__).parent.resolve()
CUSTOM_FILE = ROOT / "custom_domains.txt"
TEMPLATE_FILE = ROOT / "v2rayN-rules-template.json"
OUTPUT_FILE = ROOT / "v2rayN_rules.json"
CACHE_DIR = ROOT / "iran_domains"
UPSTREAM_WHITELIST = CACHE_DIR / "domains.txt"
UPSTREAM_BLOCKLIST = CACHE_DIR / "PersianBlockerHosts.txt"

PORT = 8765

# Load the existing generate-rules.py as a module (its filename has a dash).
_spec = importlib.util.spec_from_file_location(
    "generate_rules", str(ROOT / "generate-rules.py")
)
gr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gr)

app = Flask(__name__)
_git_lock = threading.Lock()


# ---------- custom-domain storage ----------

def load_custom_domains():
    if not CUSTOM_FILE.exists():
        return [], []
    whitelist, blocklist = [], []
    for line in CUSTOM_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "|" not in line:
            continue
        domain, kind = line.split("|", 1)
        domain = domain.strip().lower()
        kind = kind.strip().lower()
        if not domain:
            continue
        if kind == "whitelist":
            whitelist.append(domain)
        elif kind == "blocklist":
            blocklist.append(domain)
    return whitelist, blocklist


def save_custom_domains(whitelist, blocklist):
    lines = [
        "# Custom domains added via the web UI.",
        '# Format: <domain>|<list>   where <list> is "whitelist" or "blocklist".',
        "# Whitelist = routed directly (no VPN). Blocklist = blocked.",
        "# Lines starting with # are ignored.",
        "",
    ]
    for d in sorted(set(whitelist)):
        lines.append(f"{d}|whitelist")
    for d in sorted(set(blocklist)):
        lines.append(f"{d}|blocklist")
    CUSTOM_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------- rule generation ----------

def _dedup_keep_order(items):
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


_upstream_cache = {}  # {"white": set, "block": set}


def _upstream_sets():
    if "white" not in _upstream_cache:
        _upstream_cache["white"] = (
            set(gr.get_iran_domain_list()) if UPSTREAM_WHITELIST.exists() else set()
        )
        _upstream_cache["block"] = (
            set(gr.get_block_domain_list()) if UPSTREAM_BLOCKLIST.exists() else set()
        )
    return _upstream_cache["white"], _upstream_cache["block"]


def _invalidate_upstream_cache():
    _upstream_cache.clear()


def build_rules(refresh_upstream=False):
    """Re-generate v2rayN_rules.json by merging upstream + custom domains."""
    need_download = (
        refresh_upstream
        or not UPSTREAM_WHITELIST.exists()
        or not UPSTREAM_BLOCKLIST.exists()
    )
    if need_download:
        err = gr.download_domains_to_cache()
        if err:
            raise RuntimeError(err)
        _invalidate_upstream_cache()

    upstream_white = gr.get_iran_domain_list()
    upstream_block = gr.get_block_domain_list()
    custom_white, custom_block = load_custom_domains()

    # Custom domains first so they're easy to spot at the top of the rules file.
    final_white = _dedup_keep_order(custom_white + upstream_white)
    final_block = _dedup_keep_order(custom_block + upstream_block)

    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        rules = json.load(f)
    for rule in rules:
        if rule.get("id") == "ads-block":
            rule["domain"] = final_block
        elif rule.get("id") == "iran-sites":
            rule["domain"] = final_white

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(rules, f)


# ---------- git helpers ----------

def _git(*args, check=True):
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed: {result.stderr.strip()}"
        )
    return result


def commit_and_push(message):
    with _git_lock:
        _git("add", str(CUSTOM_FILE.name), str(OUTPUT_FILE.name))
        status = _git("status", "--porcelain").stdout.strip()
        if not status:
            return {"committed": False, "pushed": False, "reason": "nothing to commit"}
        _git("commit", "-m", message)
        branch = _git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        push = _git("push", "origin", branch, check=False)
        if push.returncode != 0:
            # Conflict on remote — rebase then retry once.
            pull = _git("pull", "--rebase", "origin", branch, check=False)
            if pull.returncode == 0:
                push = _git("push", "origin", branch, check=False)
        if push.returncode != 0:
            return {
                "committed": True,
                "pushed": False,
                "error": push.stderr.strip() or push.stdout.strip(),
            }
        return {"committed": True, "pushed": True}


def _format_commit(line):
    if not line or "\t" not in line:
        return None
    when, msg = line.split("\t", 1)
    return {"when": when, "message": msg}


def _subscription_url(branch):
    """Compute the raw.githubusercontent.com URL of the rules JSON."""
    remote = _git("config", "--get", "remote.origin.url", check=False).stdout.strip()
    if not remote:
        return None
    repo = None
    if remote.startswith("git@"):
        # git@github.com:user/repo.git  →  user/repo.git
        parts = remote.split(":", 1)
        if len(parts) == 2:
            repo = parts[1]
    elif remote.startswith(("https://", "http://")):
        # https://github.com/user/repo.git  →  user/repo.git
        if "github.com/" in remote:
            repo = remote.split("github.com/", 1)[1]
    if not repo:
        return None
    if repo.endswith(".git"):
        repo = repo[:-4]
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{OUTPUT_FILE.name}"


def git_status_info():
    info = {
        "branch": None,
        "local_last": None,
        "remote_last": None,
        "fetch_ok": True,
        "subscription_url": None,
    }
    try:
        info["branch"] = _git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    except Exception:
        return info

    info["subscription_url"] = _subscription_url(info["branch"])

    local = _git("log", "-1", "--format=%cI%x09%s", check=False).stdout.strip()
    info["local_last"] = _format_commit(local)

    fetch = _git("fetch", "origin", "--quiet", check=False)
    info["fetch_ok"] = fetch.returncode == 0

    remote_ref = f"origin/{info['branch']}"
    remote = _git(
        "log", "-1", "--format=%cI%x09%s", remote_ref, check=False
    ).stdout.strip()
    info["remote_last"] = _format_commit(remote)
    return info


# ---------- request validation ----------

def normalize_domain(raw):
    if not raw:
        return None
    s = raw.strip().lower()
    for prefix in ("http://", "https://"):
        if s.startswith(prefix):
            s = s[len(prefix):]
    s = s.split("/")[0]
    s = s.split(":")[0]
    if not s or " " in s or "." not in s:
        return None
    return s


# ---------- API ----------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/customs")
def api_customs():
    white, black = load_custom_domains()
    return jsonify({"whitelist": white, "blocklist": black})


@app.route("/api/upstream-counts")
def api_upstream_counts():
    try:
        w = len(gr.get_iran_domain_list()) if UPSTREAM_WHITELIST.exists() else 0
        b = len(gr.get_block_domain_list()) if UPSTREAM_BLOCKLIST.exists() else 0
    except Exception:
        w, b = 0, 0
    return jsonify({"whitelist": w, "blocklist": b})


@app.route("/api/add", methods=["POST"])
def api_add():
    data = request.get_json(force=True, silent=True) or {}
    domain = normalize_domain(data.get("domain"))
    kind = data.get("list")
    if not domain:
        return jsonify({"error": "دامنه نامعتبر است"}), 400
    if kind not in ("whitelist", "blocklist"):
        return jsonify({"error": "list باید whitelist یا blocklist باشد"}), 400

    white, black = load_custom_domains()
    target = white if kind == "whitelist" else black
    opposite = black if kind == "whitelist" else white
    opposite_name = "blocklist" if kind == "whitelist" else "whitelist"
    if domain in target:
        return jsonify({"error": "این دامنه از قبل در همین لیست هست"}), 409
    if domain in opposite:
        return jsonify({
            "error": f"این دامنه در لیست {opposite_name} هست. اول از اونجا حذفش کن."
        }), 409

    upstream_white, upstream_block = _upstream_sets()
    upstream_same = upstream_white if kind == "whitelist" else upstream_block
    if domain in upstream_same:
        return jsonify({
            "error": "این دامنه از قبل در لیست آپ‌استریم همین گروه هست — نیازی به اضافه کردن نیست."
        }), 409
    # Note: domain present in upstream of the OPPOSITE list is allowed —
    # treated as an intentional override (e.g. unblock a blocked domain).

    target.append(domain)
    save_custom_domains(white, black)

    try:
        build_rules()
    except Exception as e:
        return jsonify({"error": f"build failed: {e}"}), 500

    git_result = commit_and_push(f"add {domain} → {kind}")
    return jsonify({"ok": True, "git": git_result, "domain": domain, "list": kind})


@app.route("/api/remove", methods=["POST"])
def api_remove():
    data = request.get_json(force=True, silent=True) or {}
    domain = normalize_domain(data.get("domain"))
    kind = data.get("list")
    if not domain or kind not in ("whitelist", "blocklist"):
        return jsonify({"error": "invalid payload"}), 400

    white, black = load_custom_domains()
    target = white if kind == "whitelist" else black
    if domain not in target:
        return jsonify({"error": "پیدا نشد"}), 404
    target.remove(domain)
    save_custom_domains(white, black)

    try:
        build_rules()
    except Exception as e:
        return jsonify({"error": f"build failed: {e}"}), 500

    git_result = commit_and_push(f"remove {domain} from {kind}")
    return jsonify({"ok": True, "git": git_result, "domain": domain, "list": kind})


@app.route("/api/refresh-upstream", methods=["POST"])
def api_refresh_upstream():
    try:
        build_rules(refresh_upstream=True)
    except Exception as e:
        return jsonify({"error": f"build failed: {e}"}), 500
    git_result = commit_and_push("refresh upstream lists")
    return jsonify({"ok": True, "git": git_result})


@app.route("/api/status")
def api_status():
    return jsonify(git_status_info())


if __name__ == "__main__":
    # Ensure the output file is in sync on startup (in case custom_domains.txt
    # was edited by hand). This is cheap and avoids stale rules.
    try:
        build_rules()
    except Exception as e:
        print(f"[startup] initial build skipped: {e}")
    app.run(host="127.0.0.1", port=PORT, debug=False)
