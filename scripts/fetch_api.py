#!/usr/bin/env python3
"""API fetching module with caching. Integrates The Odds API, API-SPORTS, and MLB Stats API."""
import os
import json
import time
import requests
from pathlib import Path

ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")
API_SPORTS_KEY = os.environ.get("API_SPORTS_KEY", "")

ODDS_BASE = "https://api.the-odds-api.com/v4/sports"
API_SPORTS_BASE = "https://v3.football.api-sports.io"
MLB_BASE = "https://statsapi.mlb.com/api/v1"

CACHE_DIR = Path(__file__).parent.parent / ".cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL = 3600

ODDS_SPORT_MAP = {
    "soccer": "soccer_epl",
    "basketball": "basketball_nba",
    "baseball": "baseball_mlb",
    "tennis": "tennis_atp",
    "hockey": "icehockey_nhl",
    "handball": "handball_ehl",
}

API_SPORTS_MAP = {
    "soccer": "football",
    "basketball": "basketball",
    "baseball": "baseball",
    "tennis": "tennis",
    "hockey": "hockey",
    "handball": "handball",
}


def _cache_key(url, params):
    key = f"{url}?{json.dumps(params, sort_keys=True)}"
    return str(hash(key))


def _get_cached(key):
    cache_file = CACHE_DIR / f"{key}.json"
    if cache_file.exists():
        data = json.loads(cache_file.read_text())
        if time.time() - data["timestamp"] < CACHE_TTL:
            return data["response"]
    return None


def _set_cached(key, response):
    cache_file = CACHE_DIR / f"{key}.json"
    cache_file.write_text(json.dumps({"timestamp": time.time(), "response": response}))


def fetch_odds_api(sport_key, endpoint="odds", params=None):
    if not ODDS_API_KEY:
        print(f"[WARN] ODDS_API_KEY not set, skipping Odds API for {sport_key}")
        return None
    url = f"{ODDS_BASE}/{sport_key}/{endpoint}"
    params = params or {}
    params["apiKey"] = ODDS_API_KEY
    cache_key = _cache_key(url, params)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        _set_cached(cache_key, data)
        remaining = resp.headers.get("x-requests-remaining", "?")
        used = resp.headers.get("x-requests-used", "?")
        print(f"[ODDS API] {sport_key} - remaining: {remaining}, used: {used}")
        return data
    except requests.RequestException as e:
        print(f"[ERROR] Odds API fetch failed for {sport_key}: {e}")
        return None


def fetch_api_sports(sport, endpoint, params=None):
    if not API_SPORTS_KEY:
        print(f"[WARN] API_SPORTS_KEY not set, skipping API-SPORTS for {sport}")
        return None
    sport_code = API_SPORTS_MAP.get(sport, sport)
    base = f"https://v3.{sport_code}.api-sports.io"
    url = f"{base}/{endpoint}"
    params = params or {}
    cache_key = _cache_key(url, params)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    headers = {"x-apisports-key": API_SPORTS_KEY}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        _set_cached(cache_key, data)
        return data
    except requests.RequestException as e:
        print(f"[ERROR] API-SPORTS fetch failed for {sport}/{endpoint}: {e}")
        return None


def fetch_mlb_api(endpoint, params=None):
    url = f"{MLB_BASE}/{endpoint}"
    params = params or {}
    cache_key = _cache_key(url, params)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        _set_cached(cache_key, data)
        return data
    except requests.RequestException as e:
        print(f"[ERROR] MLB API fetch failed for {endpoint}: {e}")
        return None


def get_fixtures(sport, date_str):
    print(f"[FETCH] Getting fixtures for {sport} on {date_str}")
    if sport == "baseball":
        try:
            data = fetch_mlb_api("schedule", {"sportId": 1, "date": date_str, "hydrate": "team,venue"})
            if data and "dates" in data and data["dates"]:
                games = data["dates"][0].get("games", [])
                return [{
                    "id": str(g["gamePk"]),
                    "home_team": g["teams"]["home"]["team"]["name"],
                    "away_team": g["teams"]["away"]["team"]["name"],
                    "date": date_str,
                    "time": g.get("gameDate", ""),
                } for g in games]
        except Exception as e:
            print(f"[ERROR] MLB fixtures failed: {e}")
        return []
    data = fetch_api_sports(sport, "fixtures", {"date": date_str})
    if not data or "response" not in data:
        return []
    return [{
        "id": str(f["fixture"]["id"]),
        "home_team": f["teams"]["home"]["name"],
        "away_team": f["teams"]["away"]["name"],
        "date": date_str,
        "time": f["fixture"]["date"],
        "league_id": f["league"]["id"],
        "home_team_id": f["teams"]["home"]["id"],
        "away_team_id": f["teams"]["away"]["id"],
    } for f in data["response"]]


def get_odds(sport, date_str):
    print(f"[FETCH] Getting odds for {sport} on {date_str}")
    odds_sport = ODDS_SPORT_MAP.get(sport, sport)
    data = None
    for sport_key in [odds_sport, "upcoming"]:
        data = fetch_odds_api(sport_key, "odds", {
            "regions": "eu", "markets": "h2h,totals",
            "oddsFormat": "decimal",
            "commenceTimeFrom": f"{date_str}T00:00:00Z",
            "commenceTimeTo": f"{date_str}T23:59:59Z",
        })
        if data:
            break
    if not data:
        return {}
    odds_map = {}
    for event in data:
        event_id = event.get("id", "")
        h2h_odds = None
        totals_odds = None
        for bookmaker in event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                if market["key"] == "h2h" and not h2h_odds:
                    h2h_odds = {o["name"]: o["price"] for o in market["outcomes"]}
                if market["key"] == "totals" and not totals_odds:
                    for outcome in market["outcomes"]:
                        if outcome["name"].lower() == "over":
                            totals_odds = outcome["price"]
                            break
        odds_map[event_id] = {
            "home_team": event.get("home_team", ""),
            "away_team": event.get("away_team", ""),
            "h2h": h2h_odds,
            "over_odds": totals_odds,
        }
    return odds_map


def get_team_stats(sport, team_id, season=None):
    if sport == "baseball":
        return None
    sport_code = API_SPORTS_MAP.get(sport, sport)
    endpoints = ["teams/statistics", "statistics/teams"]
    params = {"team": team_id}
    if season:
        params["season"] = season
    for endpoint in endpoints:
        data = fetch_api_sports(sport, endpoint, params)
        if data and "response" in data:
            return data["response"]
    return None


def get_mlb_standings():
    try:
        return fetch_mlb_api("standings", {"leagueId": "103,104", "season": "2026", "sportId": "1"})
    except Exception as e:
        print(f"[ERROR] MLB standings failed: {e}")
        return None


def get_player_stats(sport, player_id):
    sport_code = API_SPORTS_MAP.get(sport, sport)
    data = fetch_api_sports(sport, "players", {"id": player_id, "season": "2026"})
    if data and "response" in data:
        return data["response"]
    return None
