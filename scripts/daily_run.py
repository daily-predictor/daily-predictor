#!/usr/bin/env python3
"""Daily Predictor - Daily pipeline runner. Fetches data, runs models, saves predictions as JSON."""
import os
import sys
import json
import traceback
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.fetch_api import get_fixtures, get_odds, get_team_stats, get_mlb_standings, get_player_stats
from sports.soccer.model import predict_match as soccer_predict, extract_team_stats_from_api as soccer_extract
from sports.basketball.model import predict_match as basketball_predict, extract_team_stats_from_api as basketball_extract
from sports.baseball.model import predict_match as baseball_predict, extract_team_stats_from_mlb as baseball_extract
from sports.tennis.model import predict_match as tennis_predict, extract_player_stats_from_api as tennis_extract
from sports.hockey.model import predict_match as hockey_predict, extract_team_stats_from_api as hockey_extract
from sports.handball.model import predict_match as handball_predict, extract_team_stats_from_api as handball_extract

SPORTS = ["soccer", "basketball", "baseball", "tennis", "hockey", "handball"]
OUTPUT_DIR = Path(__file__).parent.parent / "output"


def get_today_str():
    return date.today().strftime("%Y-%m-%d")


def ensure_output_dirs():
    for sport in SPORTS:
        (OUTPUT_DIR / sport).mkdir(parents=True, exist_ok=True)


def calculate_ev(model_prob, market_odds):
    if not market_odds or market_odds <= 0:
        return None
    return round((model_prob * market_odds) - 1, 3)


def find_market_odds(odds_map, home_team, away_team):
    for event_id, data in odds_map.items():
        odds_home = data.get("home_team", "").lower()
        odds_away = data.get("away_team", "").lower()
        match_home = home_team.lower()
        match_away = away_team.lower()
        if (match_home in odds_home or odds_home in match_home or
            match_away in odds_away or odds_away in match_away):
            h2h = data.get("h2h", {})
            return h2h.get(data["home_team"], h2h.get("Home", None))
    return None


def run_sport(sport, date_str, predict_fn, extract_fn, is_low_scoring=False, is_tennis=False, is_baseball=False):
    print(f"\n{'='*50}")
    print(f"{sport.upper()} PREDICTIONS - {date_str}")
    print(f"{'='*50}")

    fixtures = get_fixtures(sport, date_str)
    odds_map = get_odds(sport, date_str) if not is_baseball else {}
    standings = get_mlb_standings() if is_baseball else None

    predictions = []
    for fixture in fixtures:
        try:
            home_team = fixture["home_team"]
            away_team = fixture["away_team"]

            if is_baseball:
                home_stats = extract_fn(standings, fixture.get("home_team_id", "1"))
                away_stats = extract_fn(standings, fixture.get("away_team_id", "1"))
            elif is_tennis:
                home_stats_raw = get_player_stats(sport, fixture.get("home_team_id"))
                away_stats_raw = get_player_stats(sport, fixture.get("away_team_id"))
                home_stats = extract_fn(fixture, home_stats_raw)
                away_stats = extract_fn(fixture, away_stats_raw)
            else:
                home_stats_raw = get_team_stats(sport, fixture.get("home_team_id"))
                away_stats_raw = get_team_stats(sport, fixture.get("away_team_id"))
                home_stats = extract_fn(fixture, home_stats_raw)
                away_stats = extract_fn(fixture, away_stats_raw)

            result = predict_fn(home_stats, away_stats)
            market_odds = find_market_odds(odds_map, home_team, away_team)
            ev = calculate_ev(result.get("p_home"), market_odds)

            pred = {
                "match": f"{home_team} vs {away_team}",
                "p_home": result["p_home"],
                "p_away": result["p_away"],
                "fair_odds_home": result["fair_odds_home"],
                "market_odds_home": market_odds,
                "ev_home": ev,
            }

            if is_low_scoring:
                pred["p_draw"] = result["p_draw"]
                pred["ou25_over"] = result["ou25_over"]
            elif not is_tennis:
                pred["ou_over"] = result["ou_over"]

            if is_tennis:
                pred["p_win_2_0"] = result["p_win_2_0"]
                pred["sets_handicap"] = result["sets_handicap"]

            predictions.append(pred)
            print(f"OK {home_team} vs {away_team}: H={result['p_home']}, A={result['p_away']}")
        except Exception as e:
            print(f"ERR {sport} match: {e}")
            traceback.print_exc()

    return predictions


def save_predictions(sport, date_str, predictions):
    output_file = OUTPUT_DIR / sport / f"{date_str}.json"
    data = {
        "date": date_str,
        "sport": sport,
        "predictions": predictions,
        "generated_at": f"{date_str}T05:00:00Z",
    }
    output_file.write_text(json.dumps(data, indent=2))
    print(f"Saved {len(predictions)} predictions to {output_file}")


def generate_sample_data(date_str):
    print(f"\n{'='*50}")
    print("GENERATING SAMPLE DATA")
    print(f"{'='*50}")
    return {
        "soccer": [
            {"match": "Arsenal vs Chelsea", "p_home": 0.54, "p_draw": 0.24, "p_away": 0.22, "ou25_over": 0.48, "fair_odds_home": 1.85, "market_odds_home": 2.10, "ev_home": 0.07},
            {"match": "Liverpool vs Man City", "p_home": 0.31, "p_draw": 0.28, "p_away": 0.41, "ou25_over": 0.62, "fair_odds_home": 3.23, "market_odds_home": 2.80, "ev_home": -0.13},
        ],
        "basketball": [
            {"match": "Lakers vs Celtics", "p_home": 0.58, "p_away": 0.42, "ou_over": 0.55, "fair_odds_home": 1.72, "market_odds_home": 1.65, "ev_home": -0.04},
        ],
        "baseball": [
            {"match": "Yankees vs Red Sox", "p_home": 0.56, "p_away": 0.44, "ou_over": 0.51, "fair_odds_home": 1.79, "market_odds_home": None, "ev_home": None},
        ],
        "tennis": [
            {"match": "Djokovic vs Alcaraz", "p_home": 0.48, "p_away": 0.52, "p_win_2_0": 0.22, "sets_handicap": -0.2, "fair_odds_home": 2.08, "market_odds_home": None, "ev_home": None},
        ],
        "hockey": [
            {"match": "Rangers vs Bruins", "p_home": 0.45, "p_draw": 0.22, "p_away": 0.33, "ou25_over": 0.58, "fair_odds_home": 2.22, "market_odds_home": 2.40, "ev_home": -0.08},
        ],
        "handball": [
            {"match": "PSG vs Barcelona", "p_home": 0.52, "p_draw": 0.18, "p_away": 0.30, "ou25_over": 0.95, "fair_odds_home": 1.92, "market_odds_home": 1.85, "ev_home": 0.04},
        ],
    }


def main():
    date_str = get_today_str()
    print(f"\n{'#'*60}")
    print(f"# DAILY PREDICTOR - {date_str}")
    print(f"{'#'*60}")

    ensure_output_dirs()
    has_odds_key = bool(os.environ.get("ODDS_API_KEY"))
    has_sports_key = bool(os.environ.get("API_SPORTS_KEY"))
    print(f"API Keys: Odds={has_odds_key}, Sports={has_sports_key}")

    use_sample = not has_odds_key and not has_sports_key
    if use_sample:
        print("\n[!] Using sample data (no API keys configured)")
        sample_data = generate_sample_data(date_str)
        for sport, predictions in sample_data.items():
            save_predictions(sport, date_str, predictions)
        print("\nDone! Sample data generated.")
        return

    runners = {
        "soccer": lambda d: run_sport("soccer", d, soccer_predict, soccer_extract, is_low_scoring=True),
        "basketball": lambda d: run_sport("basketball", d, basketball_predict, basketball_extract),
        "baseball": lambda d: run_sport("baseball", d, baseball_predict, baseball_extract, is_baseball=True),
        "tennis": lambda d: run_sport("tennis", d, tennis_predict, tennis_extract, is_tennis=True),
        "hockey": lambda d: run_sport("hockey", d, hockey_predict, hockey_extract, is_low_scoring=True),
        "handball": lambda d: run_sport("handball", d, handball_predict, handball_extract, is_low_scoring=True),
    }

    for sport in SPORTS:
        try:
            predictions = runners[sport](date_str)
            save_predictions(sport, date_str, predictions)
        except Exception as e:
            print(f"\n[ERROR] Failed to run {sport}: {e}")
            traceback.print_exc()

    print(f"\n{'#'*60}")
    print("# DAILY PREDICTOR COMPLETE")
    print(f"{'#'*60}")


if __name__ == "__main__":
    main()
