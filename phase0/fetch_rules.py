"""
Phase 0 spike: can we read automation rules and see their structure?

What it does
  1. Looks up your site's cloudId.
  2. Lists every automation rule on the site (rule summaries).
  3. Fetches each rule's full configuration.
  4. Strips secrets (URLs, headers, tokens, passwords) before anything is saved.
  5. Prints, per rule: trigger, number of components, branches, conditions,
     and a rough "steps per run" count, so we can see if the data supports
     cost estimation.

Nothing is sent anywhere except your own Atlassian site. Redacted output is
written to phase0/output/, which is git-ignored and never committed.

Usage
  1. Copy .env.example to .env and fill in your site, email and API token.
  2. python3 phase0/fetch_rules.py

Only uses the Python standard library (Python 3.8+).
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "output"

# Keys whose values are likely to hold secrets or private endpoints.
SECRET_KEY_HINTS = (
    "url", "uri", "endpoint", "webhook", "header", "authorization", "auth",
    "token", "password", "secret", "apikey", "api_key", "key", "cookie",
    "credential", "bearer",
)
# Keys that look secret-ish by the hints above but are structural and safe.
SAFE_KEYS = {"key", "type", "component", "schemaversion", "uuid", "id"}


# ---------- setup ----------

def load_env():
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    missing = [k for k in ("ATLASSIAN_SITE", "ATLASSIAN_EMAIL", "ATLASSIAN_API_TOKEN") if not os.environ.get(k)]
    if missing:
        sys.exit(f"Missing in .env: {', '.join(missing)}. See .env.example.")
    site = os.environ["ATLASSIAN_SITE"].replace("https://", "").replace("http://", "").strip("/")
    return site, os.environ["ATLASSIAN_EMAIL"], os.environ["ATLASSIAN_API_TOKEN"]


def make_request(url, auth, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/json")
    if auth:
        req.add_header("Authorization", auth)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        return e.code, {"error": detail}
    except urllib.error.URLError as e:
        return 0, {"error": str(e.reason)}


# ---------- redaction ----------

def looks_secret(key):
    k = key.lower().replace("-", "").replace("_", "")
    if k in SAFE_KEYS:
        return False
    return any(h.replace("_", "") in k for h in SECRET_KEY_HINTS)


def mask_all(node):
    """Mask every leaf value under a secret-looking key, keeping the shape."""
    if isinstance(node, dict):
        return {k: mask_all(v) for k, v in node.items()}
    if isinstance(node, list):
        return [mask_all(v) for v in node]
    if node in (None, "", True, False):
        return node
    return "[REDACTED]"


def redact(node):
    """Return a copy with secret-looking values masked. Structure is kept."""
    if isinstance(node, dict):
        return {k: (mask_all(v) if looks_secret(k) else redact(v)) for k, v in node.items()}
    if isinstance(node, list):
        return [redact(v) for v in node]
    if isinstance(node, str) and any(m in node for m in ("http://", "https://", "Bearer ", "Basic ")):
        return "[REDACTED]"
    return node


# ---------- structure analysis ----------

def walk_components(components, depth=0, stats=None):
    """Walk a list of rule components. Field names are guesses until we see real JSON;
    unknown shapes are counted, not dropped, so the spike tells us what to fix."""
    if stats is None:
        stats = {"components": 0, "conditions": 0, "actions": 0, "branches": 0,
                 "max_depth": 0, "types": [], "unknown_shapes": 0}
    for comp in components or []:
        if not isinstance(comp, dict):
            stats["unknown_shapes"] += 1
            continue
        stats["components"] += 1
        stats["max_depth"] = max(stats["max_depth"], depth)
        kind = str(comp.get("component", "")).upper()
        ctype = comp.get("type", "?")
        stats["types"].append(ctype)
        if "CONDITION" in kind:
            stats["conditions"] += 1
        elif "BRANCH" in kind:
            stats["branches"] += 1
        elif "ACTION" in kind:
            stats["actions"] += 1
        # Nested components can appear under several keys depending on the component.
        for child_key in ("children", "conditions", "components", "then", "else"):
            child = comp.get(child_key)
            if isinstance(child, list):
                walk_components(child, depth + 1, stats)
    return stats


def summarise_rule(rule):
    body = rule.get("rule", rule)
    trigger = body.get("trigger") or {}
    stats = walk_components(body.get("components"))
    # Very rough first guess: trigger + every component runs once.
    # Branches multiply by the number of items they loop over, which needs data
    # we don't have yet. Phase 1 replaces this.
    steps_floor = 1 + stats["components"]
    return {
        "name": body.get("name", "?"),
        "state": body.get("state", "?"),
        "trigger": trigger.get("type", "?"),
        "components": stats["components"],
        "conditions": stats["conditions"],
        "actions": stats["actions"],
        "branches": stats["branches"],
        "max_depth": stats["max_depth"],
        "unknown_shapes": stats["unknown_shapes"],
        "steps_per_run_floor": steps_floor,
        "component_types": stats["types"],
    }


# ---------- main ----------

def main():
    site, email, token = load_env()
    basic = "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()
    OUT.mkdir(exist_ok=True)

    print(f"1. Looking up cloudId for {site} ...")
    status, info = make_request(f"https://{site}/_edge/tenant_info", None)
    cloud_id = info.get("cloudId")
    if not cloud_id:
        sys.exit(f"   Could not get cloudId (HTTP {status}): {info}")
    print(f"   cloudId: {cloud_id}")

    base = f"https://{site}/gateway/api/automation/public/jira/{cloud_id}/rest/v1"

    print("2. Listing rules ...")
    summaries, cursor, page = [], None, 0
    while True:
        page += 1
        body = {"cursor": cursor} if cursor else {}
        status, data = make_request(f"{base}/rule/summary", basic, "POST", body)
        if status != 200:
            print(f"   HTTP {status}: {data}")
            print("   Spike finding: listing failed. Record this in the journal.")
            break
        if page == 1:
            print(f"   Response keys: {list(data.keys())}")
        items = data.get("data") or data.get("values") or data.get("results") or []
        summaries.extend(items)
        nxt = (data.get("links") or {}).get("next") or data.get("nextCursor") or data.get("cursor")
        if not nxt or not items or nxt == cursor:
            break
        cursor = nxt.split("cursor=")[-1] if isinstance(nxt, str) and "cursor=" in nxt else nxt
    print(f"   Found {len(summaries)} rules across {page} page(s).")
    if summaries:
        print(f"   Summary fields: {list(summaries[0].keys())}")

    print("3. Fetching each rule ...")
    results = []
    for s in summaries:
        uuid = s.get("uuid") or s.get("id") or s.get("ruleUuid")
        if not uuid:
            continue
        status, full = make_request(f"{base}/rule/{uuid}", basic)
        if status != 200:
            print(f"   {uuid}: HTTP {status}")
            continue
        safe = redact(full)
        (OUT / f"rule_{uuid}.json").write_text(json.dumps(safe, indent=2))
        results.append(summarise_rule(full))

    if not results:
        print("No rule details fetched. Check the messages above.")
        return

    print("\n4. What we can see per rule\n")
    header = f"{'Rule':32} {'State':9} {'Trigger':34} {'Comp':>4} {'Cond':>4} {'Br':>3} {'Steps/run*':>10}"
    print(header)
    print("-" * len(header))
    for r in results:
        print(f"{r['name'][:32]:32} {str(r['state'])[:9]:9} {str(r['trigger'])[:34]:34} "
              f"{r['components']:>4} {r['conditions']:>4} {r['branches']:>3} {r['steps_per_run_floor']:>10}")
    print("\n* Lower bound: trigger plus each component once. Branches loop over items, so real cost can be far higher.")
    unknown = sum(r["unknown_shapes"] for r in results)
    if unknown:
        print(f"! {unknown} component(s) had a shape the parser didn't recognise. Check phase0/output/ and adjust.")

    (OUT / "summary.json").write_text(json.dumps(results, indent=2))
    print(f"\nRedacted rule files and summary.json saved in {OUT.relative_to(ROOT)}/ (git-ignored).")


if __name__ == "__main__":
    main()
