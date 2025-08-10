import os, time, csv, json
from typing import Dict, List, Any, Tuple
import yaml
from arb_math import american_to_decimal, is_two_way_arb, compute_equal_profit_stakes
from odds_providers import fetch_the_odds_api
from telegram_helper import send_message
from datetime import datetime


print(f"Service started successfully 🚀 at {datetime.now()}")


CACHE_PATH = "sent_cache.json"

def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)

def read_mock_odds(path: str) -> List[Dict[str, Any]]:
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            r["american_odds"] = int(r["american_odds"])
            rows.append(r)
    return rows

def group_by_event(records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    for r in records:
        key = f"{r['sport']}|{r['event']}"
        out.setdefault(key, []).append(r)
    return out

def best_price_per_team(event_rows: List[Dict[str, Any]], allowed_books: List[str]) -> List[Dict[str, Any]]:
    filtered = [r for r in event_rows if r["book"] in allowed_books]
    by_team: Dict[str, Dict[str, Any]] = {}
    for r in filtered:
        t = r["team"]
        if t not in by_team:
            by_team[t] = r
        else:
            cur = by_team[t]
            new_odds = r["american_odds"]
            old_odds = cur["american_odds"]
            better = False
            if new_odds > 0 and old_odds > 0:
                better = new_odds > old_odds
            elif new_odds < 0 and old_odds < 0:
                better = abs(new_odds) < abs(old_odds)
            else:
                better = new_odds > old_odds
            if better:
                by_team[t] = r
    return list(by_team.values())

def calc_roi(d1: float, d2: float) -> float:
    return 1.0 - (1.0/d1 + 1.0/d2)

def scale_to_cap(s1: float, s2: float, profit: float, cap: float) -> Tuple[float, float, float]:
    m = max(s1, s2)
    if m <= cap:
        return s1, s2, profit
    factor = cap / m
    return s1 * factor, s2 * factor, profit * factor

def format_alert(event: str, side1: Dict[str, Any], side2: Dict[str, Any], s1: float, s2: float, profit: float, roi: float) -> str:
    lines = []
    lines.append(f"Arbitrage found: {event}")
    lines.append(f"Bet 1: {side1['team']} at {side1['book']} odds {side1['american_odds']} stake ${s1:.2f}")
    lines.append(f"Bet 2: {side2['team']} at {side2['book']} odds {side2['american_odds']} stake ${s2:.2f}")
    lines.append(f"Guaranteed profit: ${profit:.2f}")
    lines.append(f"Edge: {roi*100:.2f}%")
    return "\n".join(lines)

def arb_signature(event: str, a: Dict[str, Any], b: Dict[str, Any], roi: float) -> str:
    sides = sorted([
        (a["book"], a["team"], a["american_odds"]),
        (b["book"], b["team"], b["american_odds"]),
    ])
    roi_key = round(roi, 4)
    return f"{event}|{sides[0]}|{sides[1]}|roi={roi_key}"

def load_cache() -> Dict[str, float]:
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache(c: Dict[str, float]) -> None:
    with open(CACHE_PATH, "w") as f:
        json.dump(c, f)

def run_once(cfg: dict) -> List[Tuple[str, str]]:
    bankroll = float(cfg.get("bankroll", 1000))
    min_roi = float(cfg.get("min_roi", 0.01))
    cap = float(cfg.get("max_stake_per_side", 5.0))
    allowed_books = cfg.get("books", [])

    if cfg.get("use_mock_data", True):
        records = read_mock_odds("sample_odds.csv")
    else:
        o = cfg.get("odds_api", {})
        records = fetch_the_odds_api(
            api_key=o.get("api_key", ""),
            regions=o.get("regions", "us"),
            markets=o.get("markets", "h2h"),
            odds_format=o.get("odds_format", "american"),
            bookmakers=o.get("bookmakers", ["DraftKings", "BetMGM", "FanDuel"])
        )

    events = group_by_event(records)
    alerts: List[Tuple[str, str]] = []
    for event_key, rows in events.items():
        picks = best_price_per_team(rows, allowed_books)
        if len(picks) != 2:
            continue
        a, b = picks[0], picks[1]
        d1 = american_to_decimal(a["american_odds"])
        d2 = american_to_decimal(b["american_odds"])
        if not is_two_way_arb(d1, d2):
            continue
        roi = calc_roi(d1, d2)
        if roi < min_roi:
            continue
        s1, s2, prof = compute_equal_profit_stakes(bankroll, d1, d2)
        s1, s2, prof = scale_to_cap(s1, s2, prof, cap)
        event_name = event_key.split("|", 1)[1]
        alert = format_alert(event_name, a, b, s1, s2, prof, roi)
        sig = arb_signature(event_name, a, b, roi)
        alerts.append((alert, sig))
    return alerts

def main():
    cfg = load_config("config.yaml")
    bot_token = cfg["telegram"]["bot_token"]
    chat_id = cfg["telegram"]["chat_id"]
    dedupe_minutes = int(cfg.get("dedupe_minutes", 120))
    interval = int(cfg.get("scan_interval_seconds", 60))

    cache = load_cache()

    if cfg.get("use_mock_data", True):
        alerts = run_once(cfg)
        now = time.time()
        ttl = dedupe_minutes * 60
        cache = {k:v for k,v in cache.items() if now - v < ttl}
        for msg, sig in alerts:
            if sig in cache:
                continue
            print(msg)
            send_message(bot_token, chat_id, msg)
            cache[sig] = now
        save_cache(cache)
        return

    print(f"Scanner live. Interval {interval}s. Dedupe {dedupe_minutes}m.")
    while True:
        try:
            start = time.time()
            alerts = run_once(cfg)

            now = time.time()
            ttl = dedupe_minutes * 60
            cache = {k:v for k,v in cache.items() if now - v < ttl}

            sent = 0
            for msg, sig in alerts:
                if sig in cache:
                    continue
                print(msg)
                send_message(bot_token, chat_id, msg)
                cache[sig] = now
                sent += 1

            save_cache(cache)
            if sent == 0:
                print(f"scan tick {time.strftime('%H:%M:%S')} no new arbs")
        except Exception as e:
            if "429" in str(e):
                print("Rate limited. Sleeping 60s.")
                time.sleep(60)
            else:
                print(f"Scan error: {e}")
        elapsed = time.time() - start
        sleep_for = max(0, interval - elapsed)
        time.sleep(sleep_for)

if __name__ == "__main__":
    main()
