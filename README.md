[![fa](https://img.shields.io/badge/lang-fa-red.svg) فارسی](README.fa-IR.md)

# v2rayN Routing Rules Generator + Web UI

A Python tool that generates routing rules in JSON format for the
[v2rayN](https://github.com/2dust/v2rayN) application, with a lightweight
local **web UI** for managing your own custom domains on top of the
upstream lists.

The main goal of these rules is to keep Iranian sites direct (no VPN)
so they don't break, while everything else goes through the proxy.

Forked from [mer30hamid/v2rayN-Routing-Rules-Generator](https://github.com/mer30hamid/v2rayN-Routing-Rules-Generator).

## What this fork adds

- **Web UI** ([app.py](app.py)) to add/remove domains without editing files by hand.
- **Custom domains layer** ([custom_domains.txt](custom_domains.txt)) merged
  on top of the upstream lists, so the upstream refresh never wipes your
  manual entries. Custom domains are placed at the top of the final list.
- **Auto commit + push** to `origin` on every change — the subscription
  URL is always serving the latest rules.
- **Updated template** matching the v2rayN UI: per-rule `Remarks`,
  `ruleType: 1` (== "routing"), and a saner default rule order so the
  subscription works without any manual fix-up after import.

## Subscription URL

Use this in v2rayN as a subscription URL:

```
https://raw.githubusercontent.com/aminmoghadas/v2rayN-Routing-Rules-Generator/main/v2rayN_rules.json
```

## Web UI

Lightweight Flask app on `http://127.0.0.1:8765` (loopback only). One
page; pick a tab, type a domain (or full URL — it's normalized), click
**Add**. The backend re-builds `v2rayN_rules.json`, commits, and pushes
to `origin/main`. The next time v2rayN refreshes the subscription, your
new entry is live.

What it does:

- Whitelist tab (rules → `direct`, used for Iranian sites that should
  bypass the VPN) and Blocklist tab (rules → `block`).
- Normalizes input: `https://Foo.COM/path` → `foo.com`.
- Duplicate guard: rejects entries already in the same custom list,
  in the opposite custom list, or already covered by the upstream list.
- Shows the subscription URL with a copy button.
- Shows last local commit and last `origin/main` commit.
- "Refresh upstream lists" button to manually re-download the SamadiPour
  and PersianBlocker lists.

### Run it

First time:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Then:

```bash
.venv/bin/python app.py
```

Open `http://127.0.0.1:8765`.

> Note: the UI is bound to `127.0.0.1` only and pushes via your existing
> git SSH/HTTPS auth — there is no separate auth layer.

## Importing the rules into v2rayN

1. In v2rayN: **Settings → Routing Setting → Add Rule**.
2. **Remarks**: `Iran` (or anything).
3. **URL (optional)**: paste the subscription URL above.
4. Click **Import Rules From Subscription URL**, confirm.
5. In the routing panel at the bottom of v2rayN, select your new entry.

After the first import you don't have to repeat these steps — v2rayN
fetches the latest rules from the subscription URL on demand
(right-click the subscription → Update) or on its auto-update interval
(configurable in v2rayN's general settings).

## Running the generator without the UI

If you just want the JSON, the original entry point still works:

```bash
.venv/bin/python generate-rules.py
```

This produces `v2rayN_rules.json` with the upstream lists only (no
custom entries) and updates the cache under `iran_domains/`.

## Files

| Path | What it is |
|---|---|
| [generate-rules.py](generate-rules.py) | Original CLI generator |
| [app.py](app.py) | Flask web UI + git push logic |
| [templates/index.html](templates/index.html) | Single-page UI |
| [v2rayN-rules-template.json](v2rayN-rules-template.json) | Rule skeleton |
| [v2rayN_rules.json](v2rayN_rules.json) | Generated output (committed) |
| [custom_domains.txt](custom_domains.txt) | Your custom domains |
| [iran_domains/](iran_domains/) | Cached upstream lists (gitignored) |

## Upstream sources

- [SamadiPour/iran-hosted-domains](https://github.com/SamadiPour/iran-hosted-domains) — Iranian sites whitelist
- [MasterKia/PersianBlocker](https://github.com/MasterKia/PersianBlocker) — Persian ads/tracker blocklist
