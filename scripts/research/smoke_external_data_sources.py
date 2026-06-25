"""Phase 3B — OFFLINE external-data recon smoke tests (READ-ONLY, no production touch).

Minimal (~1 request/provider) auth + capability probe for the 4 providers. SECRET-SAFE:
  - keys loaded ONLY from .env.yorian (gitignored),
  - key VALUES are never printed and are scrubbed from every saved sample,
  - no key is sent to an unidentified host (TheOdds.io is probed keyless until identified).

No betting execution, no scraping behind login, no quota-rotation. Writes sanitized outputs to
outputs/research/phase_3b_external_data/. Does NOT touch production model/app/data/config.

Run:  PYTHONPATH=src .venv/bin/python scripts/research/smoke_external_data_sources.py
"""
from __future__ import annotations

import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
ENV = ROOT / ".env.yorian"
OUT = ROOT / "outputs" / "research" / "phase_3b_external_data"
TIMEOUT = 12


def load_keys() -> dict:
    keys = {}
    for line in ENV.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        keys[k.strip()] = v.strip().strip('"').strip("'")
    return keys


def scrub(obj, secrets):
    """Recursively redact any string equal to / containing a secret value."""
    sset = [s for s in secrets if s]
    if isinstance(obj, dict):
        return {k: scrub(v, sset) for k, v in obj.items()}
    if isinstance(obj, list):
        return [scrub(v, sset) for v in obj]
    if isinstance(obj, str):
        for s in sset:
            if s and s in obj:
                return "***REDACTED***"
    return obj


def top_fields(obj, depth=0):
    if isinstance(obj, dict):
        return sorted(obj.keys())
    if isinstance(obj, list) and obj:
        return top_fields(obj[0])
    return []


def save(name, secrets, **payload):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(scrub(payload, secrets), indent=2)[:8000])


def the_odds_api(keys):
    s = keys.get("THE_ODDS_API_KEY", "")
    r = requests.get("https://api.the-odds-api.com/v4/sports/", params={"apiKey": s}, timeout=TIMEOUT)
    body = r.json() if r.ok else r.text
    soccer = [x.get("key") for x in (body or []) if isinstance(x, dict) and x.get("group") == "Soccer"] if r.ok else []
    quota = {h: r.headers.get(h) for h in ("x-requests-remaining", "x-requests-used", "x-requests-last")}
    save("the_odds_api", [s], status=r.status_code, quota=quota,
         sample_sport=(body[0] if r.ok and body else body), soccer_keys=soccer[:20])
    return {
        "provider": "The Odds API (the-odds-api.com)", "auth": "ok" if r.ok else f"FAIL {r.status_code}",
        "http": r.status_code, "endpoint": "GET /v4/sports",
        "fields": top_fields(body) if r.ok else [],
        "quota": quota,
        "useful": f"{len(soccer)} soccer markets listed" + (" incl. World Cup" if any("world_cup" in (k or "") for k in soccer) else ""),
    }


def _af_parse(body):
    """API-Football /status: response is a dict on success, [] on auth failure."""
    resp = body.get("response") if isinstance(body, dict) else None
    resp = resp if isinstance(resp, dict) else {}
    errors = body.get("errors") if isinstance(body, dict) else None
    return resp, errors


def api_football(keys):
    s = keys.get("API_FOOTBALL_KEY", "")
    # Try direct api-sports.io first; if rejected, try the RapidAPI host once.
    attempts = [
        ("direct (x-apisports-key)", "https://v3.football.api-sports.io/status", {"x-apisports-key": s}),
        ("rapidapi (x-rapidapi-key)", "https://api-football-v1.p.rapidapi.com/v3/status",
         {"x-rapidapi-key": s, "x-rapidapi-host": "api-football-v1.p.rapidapi.com"}),
    ]
    last = {}
    for how, url, hdr in attempts:
        try:
            r = requests.get(url, headers=hdr, timeout=TIMEOUT)
            body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        except Exception as e:
            last = {"how": how, "status": "ERR", "err": str(e)[:80]}; continue
        resp, errors = _af_parse(body)
        last = {"how": how, "status": r.status_code, "resp": resp, "errors": errors}
        if r.status_code == 200 and resp and not errors:
            break
    resp = last.get("resp", {}) or {}
    sub = resp.get("subscription", {}) or {}; req = resp.get("requests", {}) or {}
    ok = bool(resp) and not last.get("errors")
    save("api_football", [s], working_path=last.get("how"), status=last.get("status"),
         response=resp, errors=last.get("errors"))
    return {
        "provider": "API-Football (api-sports.io / RapidAPI)",
        "auth": "ok" if ok else f"FAIL {last.get('status')}",
        "http": last.get("status"), "endpoint": f"GET /status [{last.get('how')}]",
        "fields": top_fields(resp),
        "quota": {"plan": sub.get("plan"), "active": sub.get("active"),
                  "requests_day": f"{req.get('current')}/{req.get('limit_day')}"} if ok else
                 {"errors": str(last.get("errors"))[:120]},
        "useful": "plan/quota visible" if ok else "key rejected on both direct + RapidAPI hosts",
    }


def sportmonks(keys):
    s = keys.get("SPORTMONKS_TOKEN", "")
    r = requests.get("https://api.sportmonks.com/v3/football/leagues",
                     params={"api_token": s, "per_page": 1}, timeout=TIMEOUT)
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    save("sportmonks", [s], status=r.status_code,
         subscription=body.get("subscription"), rate_limit=body.get("rate_limit"),
         sample_league=(body.get("data") or [None])[0], message=body.get("message"))
    ok = r.status_code == 200 and bool(body.get("data"))
    subs = body.get("subscription") or []
    plan = (subs[0].get("plans", [{}])[0].get("plan") if subs and isinstance(subs, list) else None)
    return {
        "provider": "Sportmonks (api.sportmonks.com/v3/football)", "auth": "ok" if ok else f"FAIL {r.status_code}",
        "http": r.status_code, "endpoint": "GET /v3/football/leagues",
        "fields": top_fields((body.get("data") or [None])[0] or {}),
        "quota": {"plan": plan, "rate_limit": body.get("rate_limit")},
        "useful": "leagues readable" if ok else (body.get("message") or "")[:80],
    }


def theodds_io(keys):
    """Provider identity ambiguous ('theodds.io' vs odds-api.io vs theoddsapi.com).
    Probe the LITERAL domain keyless to identify it; do NOT send the key to a guessed host."""
    present = bool(keys.get("THEODDS_IO_KEY"))
    status, note = "unreachable", ""
    for host in ("https://api.theodds.io/", "https://theodds.io/"):
        try:
            r = requests.get(host, timeout=8)
            status, note = r.status_code, (r.headers.get("content-type", "") + " | " + r.text[:80].replace("\n", " "))
            break
        except Exception as e:
            note = f"{type(e).__name__}: {str(e)[:80]}"
    save("theodds_io", [keys.get("THEODDS_IO_KEY", "")], literal_probe={"status": str(status), "note": note},
         key_present=present, key_sent=False)
    return {
        "provider": "TheOdds.io (UNVERIFIED domain)", "auth": "NOT TESTED (key withheld)",
        "http": status, "endpoint": "keyless probe of literal domain",
        "fields": [], "quota": {}, "useful": "key present but provider identity ambiguous — needs confirmation",
    }


def main():
    keys = load_keys()
    secrets = [v for v in keys.values() if v]
    print("Keys loaded from .env.yorian (values hidden):")
    for k in ("THE_ODDS_API_KEY", "API_FOOTBALL_KEY", "THEODDS_IO_KEY", "SPORTMONKS_TOKEN"):
        print(f"  {k}: {'present (len %d)' % len(keys[k]) if keys.get(k) else 'MISSING'}")
    print()

    results = []
    for fn in (the_odds_api, api_football, sportmonks, theodds_io):
        try:
            results.append(fn(keys))
        except Exception as e:
            results.append({"provider": fn.__name__, "auth": f"ERROR {type(e).__name__}",
                            "http": "-", "endpoint": "-", "fields": [], "quota": {}, "useful": str(e)[:100]})

    import csv
    with (OUT / "provider_capability_matrix.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["provider", "auth_status", "http", "endpoint", "fields_confirmed", "quota_plan", "useful_data"])
        for r in results:
            w.writerow([r["provider"], r["auth"], r["http"], r["endpoint"],
                        "|".join(r["fields"][:12]), json.dumps(r["quota"]), r["useful"]])

    print("=== SMOKE RESULTS (sanitized) ===")
    for r in results:
        print(f"\n[{r['provider']}]\n  auth: {r['auth']} (HTTP {r['http']}) · {r['endpoint']}"
              f"\n  fields: {r['fields'][:12]}\n  quota: {r['quota']}\n  useful: {r['useful']}")
    print(f"\nWrote {OUT}/provider_capability_matrix.csv + sanitized per-provider JSON.")


if __name__ == "__main__":
    main()
