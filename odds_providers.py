import requests
from typing import List, Dict, Any

def fetch_the_odds_api(api_key: str, regions: str, markets: str, odds_format: str, bookmakers: List[str]) -> List[Dict[str, Any]]:
    url = "https://api.the-odds-api.com/v4/sports/upcoming/odds"
    params = {
        "apiKey": api_key,
        "regions": regions,
        "markets": markets,
        "oddsFormat": odds_format,
        "bookmakers": ",".join(bookmakers),
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    records: List[Dict[str, Any]] = []
    for ev in data:
        home = ev.get("home_team", "")
        away = ev.get("away_team", "")
        event_name = f"{home} vs {away}" if home and away else ev.get("commence_time", "Unknown event")
        sport_key = ev.get("sport_key", "unknown")
        for book in ev.get("bookmakers", []):
            book_name = book.get("title", "unknown")
            for market in book.get("markets", []):
                if market.get("key") != markets:
                    continue
                for outcome in market.get("outcomes", []):
                    team = outcome.get("name", "unknown")
                    price = outcome.get("price")
                    if price is None:
                        continue
                    try:
                        american_price = int(price)
                    except Exception:
                        continue
                    records.append({
                        "sport": sport_key,
                        "event": event_name,
                        "book": book_name,
                        "team": team,
                        "american_odds": american_price,
                    })
    return records
