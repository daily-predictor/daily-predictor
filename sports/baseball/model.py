#!/usr/bin/env python3
"""Baseball prediction model using Pythagorean expectation + Poisson."""
import math

PYTHAG_EXPONENT = 1.82
LEAGUE_AVG_RUNS = 4.5
MAX_GOALS = 6


def poisson_pmf(k, lam):
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def pythagorean_win_pct(runs_scored, runs_allowed):
    rs_exp = runs_scored ** PYTHAG_EXPONENT
    ra_exp = runs_allowed ** PYTHAG_EXPONENT
    return rs_exp / (rs_exp + ra_exp)


def calculate_probabilities(home_rs_per_game, home_ra_per_game,
                            away_rs_per_game, away_ra_per_game,
                            park_factor=1.0, league_avg=LEAGUE_AVG_RUNS, total_line=8.5):
    lam_home = (home_rs_per_game * away_ra_per_game / league_avg) * park_factor
    lam_away = (away_rs_per_game * home_ra_per_game / league_avg) * park_factor

    p_home = [poisson_pmf(k, lam_home) for k in range(MAX_GOALS + 1)]
    p_away = [poisson_pmf(k, lam_away) for k in range(MAX_GOALS + 1)]

    p_home_win = sum(p_home[i] * p_away[j] for i in range(1, MAX_GOALS + 1) for j in range(i))
    p_draw = sum(p_home[i] * p_away[i] for i in range(MAX_GOALS + 1))
    p_away_win = 1.0 - p_home_win - p_draw
    p_over = sum(p_home[i] * p_away[j] for i in range(MAX_GOALS + 1) for j in range(MAX_GOALS + 1) if i + j > total_line)

    home_pyth = pythagorean_win_pct(home_rs_per_game, home_ra_per_game)
    away_pyth = pythagorean_win_pct(away_rs_per_game, away_ra_per_game)

    return {
        "p_home": round(p_home_win, 4),
        "p_draw": round(p_draw, 4),
        "p_away": round(p_away_win, 4),
        "ou_line": total_line,
        "ou_over": round(p_over, 4),
        "fair_odds_home": round(1.0 / p_home_win, 2) if p_home_win > 0 else 999,
        "fair_odds_away": round(1.0 / p_away_win, 2) if p_away_win > 0 else 999,
        "pythagorean_home": round(home_pyth, 4),
        "pythagorean_away": round(away_pyth, 4),
        "lambda_home": round(lam_home, 3),
        "lambda_away": round(lam_away, 3),
    }


def predict_match(home_team_stats, away_team_stats, park_factor=1.0, total_line=8.5):
    return calculate_probabilities(
        home_team_stats.get("rs_per_game", 4.5),
        home_team_stats.get("ra_per_game", 4.5),
        away_team_stats.get("rs_per_game", 4.5),
        away_team_stats.get("ra_per_game", 4.5),
        park_factor=park_factor,
        total_line=total_line
    )


def extract_team_stats_from_mlb(standings_data, team_id):
    if not standings_data or "records" not in standings_data:
        return {"rs_per_game": 4.5, "ra_per_game": 4.5}
    try:
        for record in standings_data["records"]:
            for team_record in record.get("teamRecords", []):
                if str(team_record["team"]["id"]) == str(team_id):
                    rs = team_record.get("runsScored", 0)
                    ra = team_record.get("runsAllowed", 0)
                    games = team_record.get("gamesPlayed", 1)
                    return {
                        "rs_per_game": rs / max(1, games),
                        "ra_per_game": ra / max(1, games),
                    }
    except Exception as e:
        print(f"[WARN] Could not extract MLB team stats: {e}")
    return {"rs_per_game": 4.5, "ra_per_game": 4.5}
