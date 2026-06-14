"""Live WC2026 engine.

Fetches in-progress + finished matches from the provider router (API-Football is
primary for live/today), resolves each match's group from groups.json, and merges
newly-finished results into data/wc2026_live.json with recomputed standings/points.

Design goal: the dashboard can call `fetch_live_state()` on a timer and the site updates
itself — new matches appear live, scores tick, and a result is locked in (full-time)
into the standings automatically. Everything here is FAILURE-SAFE: any provider, network,
key, or parse error returns the last-known state and never raises, so the UI never crashes
(offline / no-keys / quota-exhausted all degrade gracefully).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parents[2]
_DATA = _ROOT / "data"
LIVE_PATH = _DATA / "wc2026_live.json"
GROUPS_PATH = _DATA / "groups.json"

# status buckets
_LIVE_STATUSES = {"1H", "HT", "2H", "ET", "BT", "P", "LIVE", "IN_PLAY"}
_DONE_STATUSES = {"FT", "AET", "PEN", "FINISHED"}


def _team_group_map() -> dict[str, str]:
    if not GROUPS_PATH.exists():
        return {}
    groups = json.loads(GROUPS_PATH.read_text())
    return {code: grp for grp, codes in groups.items() for code in codes}


def _resolve_group(m, tgmap: dict[str, str]) -> str:
    return getattr(m, "group", "") or tgmap.get(m.home, "") or tgmap.get(m.away, "") or ""


def _m2d(m, tgmap) -> dict:
    return {
        "home": m.home, "away": m.away,
        "home_goals": m.home_goals, "away_goals": m.away_goals,
        "date": getattr(m, "date", "") or "",
        "group": _resolve_group(m, tgmap),
        "status": getattr(m, "status", "") or "",
        "minute": getattr(m, "minute", None),
        "scorers": list(getattr(m, "scorers_home", []) or []) + list(getattr(m, "scorers_away", []) or []),
        "source": getattr(m, "provider", "") or "",
    }


def fetch_live_state() -> dict:
    """Return current live state. Never raises.

    Keys: ok, generated_at, live[], finished[], all_completed[], error.
    `live` = in-progress matches (score + minute). `finished` = today's FT matches.
    `all_completed` = every finished WC2026 match seen by the providers.
    """
    out = {"ok": False, "generated_at": datetime.now(timezone.utc).isoformat(),
           "live": [], "finished": [], "all_completed": [], "error": ""}
    try:
        from .providers.router import ProviderRouter
        tg = _team_group_map()
        router = ProviderRouter()
        try:
            live = [_m2d(m, tg) for m in (router.get_live_matches() or [])]
        except Exception:
            live = []
        try:
            completed = [_m2d(m, tg) for m in (router.get_completed_matches() or [])]
        except Exception:
            completed = []
        # de-dup completed by (home,away,date)
        seen, uniq = set(), []
        for c in completed:
            k = (c["home"], c["away"], c["date"])
            if k not in seen and c["home_goals"] is not None:
                seen.add(k); uniq.append(c)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out.update(ok=True, live=live, all_completed=uniq,
                   finished=[c for c in uniq if c["date"] == today])
    except Exception as e:  # router construction or import failure
        out["error"] = f"{type(e).__name__}: {e}"
    return out


def build_standings(completed: list[dict]) -> dict[str, list[dict]]:
    """Group tables (points/GD/GF) from completed matches; fills all teams from groups.json."""
    tg = _team_group_map()
    table: dict[str, dict] = {}
    for m in completed:
        grp = m.get("group") or tg.get(m["home"], "") or tg.get(m["away"], "")
        if not grp or m.get("home_goals") is None:
            continue
        for team, gf, ga in [(m["home"], m["home_goals"], m["away_goals"]),
                             (m["away"], m["away_goals"], m["home_goals"])]:
            r = table.setdefault(team, {"team": team, "group": grp, "played": 0, "won": 0,
                                        "drawn": 0, "lost": 0, "gf": 0, "ga": 0, "gd": 0, "points": 0})
            r["played"] += 1; r["gf"] += gf; r["ga"] += ga; r["gd"] = r["gf"] - r["ga"]
            if gf > ga:   r["won"] += 1; r["points"] += 3
            elif gf == ga: r["drawn"] += 1; r["points"] += 1
            else:          r["lost"] += 1
    groups_out: dict[str, list[dict]] = {}
    for row in table.values():
        groups_out.setdefault(row["group"], []).append(row)
    if GROUPS_PATH.exists():
        for grp, codes in json.loads(GROUPS_PATH.read_text()).items():
            groups_out.setdefault(grp, [])
            have = {r["team"] for r in groups_out[grp]}
            for code in codes:
                if code not in have:
                    groups_out[grp].append({"team": code, "group": grp, "played": 0, "won": 0,
                                            "drawn": 0, "lost": 0, "gf": 0, "ga": 0, "gd": 0, "points": 0})
    for grp in groups_out:
        groups_out[grp].sort(key=lambda r: (-r["points"], -r["gd"], -r["gf"], r["team"]))
    return groups_out


def merge_and_persist(state: dict) -> dict:
    """Merge newly-finished matches into wc2026_live.json, recompute standings, write if changed.

    Returns {"n_new": int, "total": int, "changed": bool}. Never raises.
    """
    res = {"n_new": 0, "total": 0, "changed": False}
    try:
        existing = json.loads(LIVE_PATH.read_text()) if LIVE_PATH.exists() else {}
        cur = existing.get("completed_matches", [])
        tg = _team_group_map()
        # Index by (home,away) — each group-stage pair plays exactly once, so this
        # both de-dups any pre-existing duplicates and lets provider results update scores.
        by_pair: dict[tuple, dict] = {}
        for c in cur:
            by_pair[(c["home"], c["away"])] = c
        before_keys = set(by_pair)
        changed_scores = 0
        for c in state.get("all_completed", []):
            if c["home_goals"] is None:
                continue
            key = (c["home"], c["away"])
            prev = by_pair.get(key)
            entry = {"date": c["date"], "group": c["group"] or tg.get(c["home"], ""),
                     "matchday": (prev or {}).get("matchday", 1),
                     "home": c["home"], "away": c["away"],
                     "home_goals": c["home_goals"], "away_goals": c["away_goals"],
                     "decided_in": (prev or {}).get("decided_in", "90"),
                     "scorers": c.get("scorers") or (prev or {}).get("scorers", []),
                     "notes": (prev or {}).get("notes", ""),
                     "source": c.get("source", "live")}
            if prev and (prev.get("home_goals"), prev.get("away_goals")) != (c["home_goals"], c["away_goals"]):
                changed_scores += 1
            by_pair[key] = entry
        merged = sorted(by_pair.values(), key=lambda x: (x.get("date", ""), x["home"]))
        new_keys = set(by_pair) - before_keys
        res["n_new"] = len(new_keys); res["total"] = len(merged)
        had_dupes = len(cur) != len(before_keys)
        # Prune any finished match out of upcoming_today so the persisted data is truthful
        # too (not just filtered at render). Fixes the QAT-SUI "completed + upcoming" duplicate.
        done_pairs = set(by_pair)
        up = existing.get("upcoming_today")
        up_pruned = [m for m in up if (m.get("home"), m.get("away")) not in done_pairs] if up else up
        up_changed = up is not None and len(up_pruned) != len(up)
        if new_keys or changed_scores or had_dupes or up_changed:
            existing["completed_matches"] = merged
            if up_pruned is not None:
                existing["upcoming_today"] = up_pruned
            existing["group_standings"] = build_standings(merged)
            existing["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            existing.setdefault("tournament", "FIFA World Cup 2026")
            LIVE_PATH.write_text(json.dumps(existing, indent=2))
            res["changed"] = True
    except Exception:
        pass
    return res
