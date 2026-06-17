#!/usr/bin/env python3
"""Soccer prediction model using Poisson distribution."""
import math

HOME_ADV = 1.12
LEAGUE_AVG_GOALS = 2.67
MAX_GOALS = 6


def poisson_pmf(k, lam):
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def calculate_probabilities(home_attack, away_attack, home_defence, away_defence,
                            rest_factor=1.0, league_avg=LEAGUE_AVG_GOALS):
    lam_home = home_attack * away_defence * league_avg * HOME_ADV * rest_factor
    lam_away = away_attack * home_defence * league_avg * rest_factor

    p_home = [poisson_pmf(k, lam_home) for k in range(MAX_GOALS + 1)]
    p_away = [poisson_pmf(k, lam_away) for k in range(MAX_GOALS + 1)]

    p_home_win = sum(p_home[i] * p_away[j] for i in range(1, MAX_GOALS + 1) for j in range(i))
    p_draw = sum(p_home[i] * p_away[i] for i in range(MAX_GOALS + 1))
    p_away_win = 1.0 - p_home_win - p_draw
    p_over_2_5 = sum(p_home[i] * p_away[j] for i in range(MAX_GOALS + 1) for j in range(MAX_GOALS + 1) if i + j > 2.5)

    return {
        "p_home": round(p_home_win, 4),
        "p_draw": round(p_draw, 4),
        "p_away": round(p_away_win, 4),
        "ou25_over": round(p_over_2_5, 4),
        "fair_odds_home": round(1.0 / p_home_win, 2) if p_home_win > 0 else 999,
        "fair_odds_draw": round(1.0 / p_draw, 2) if p_draw > 0 else 999,
        "fair_odds_away": round(1.0 / p_away_win, 2) if p_away_win > 0 else 999,
        "lambda_home": round(lam_home, 3),
        "lambda_away": round(lam_away, 3),
    }


def predict_match(home_team_stats, away_team_stats, league_avg=LEAGUE_AVG_GOALS):
    return calculate_probabilities(
        home_team_stats.get("attack", 1.0),
        away_team_stats.get("attack", 1.0),
        home_team_stats.get("defence", 1.0),
        away_team_stats.get("defence", 1.0),
        rest_factor=home_team_stats.get("rest_factor", 1.0),
        league_avg=league_avg
    )


def extract_team_stats_from_api(fixture_data, team_stats_response):
    if not team_stats_response:
        return {"attack": 1.0, "defence": 1.0, "rest_factor": 1.0}
    try:
        stats = team_stats_response[0] if isinstance(team_stats_response, list) and len(team_stats_response) > 0 else team_stats_response
        goals_for = stats.get("goals", {}).get("for", {}).get("average", {}).get("total", 1.34)
        goals_against = stats.get("goals", {}).get("against", {}).get("average", {}).get("total", 1.34)
        attack = float(goals_for) / (LEAGUE_AVG_GOALS / 2)
        defence = float(goals_against) / (LEAGUE_AVG_GOALS / 2)
        return {
            "attack": max(0.5, min(2.0, attack)),
            "defence": max(0.5, min(2.0, defence)),
            "rest_factor": 1.0,
        }
    except Exception as e:
        print(f"[WARN] Could not extract team stats: {e}")
        return {"attack": 1.0, "defence": 1.0, "rest_factor": 1.0}
