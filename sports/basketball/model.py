#!/usr/bin/env python3
"""Basketball prediction model using Normal distribution."""
from scipy.stats import norm

SIGMA_DIFF = 11.0
SIGMA_TOTAL = 14.0


def calculate_probabilities(home_off_rtg, away_off_rtg, pace, total_line=220.5):
    mu_home = pace * home_off_rtg / 100.0
    mu_away = pace * away_off_rtg / 100.0
    mu_diff = mu_home - mu_away + 2.5
    p_home = norm.cdf(mu_diff / SIGMA_DIFF)
    p_away = 1.0 - p_home
    mu_total = mu_home + mu_away
    p_over = 1.0 - norm.cdf((total_line - mu_total) / SIGMA_TOTAL)
    return {
        "p_home": round(p_home, 4),
        "p_away": round(p_away, 4),
        "ou_line": total_line,
        "ou_over": round(p_over, 4),
        "fair_odds_home": round(1.0 / p_home, 2) if p_home > 0 else 999,
        "fair_odds_away": round(1.0 / p_away, 2) if p_away > 0 else 999,
        "mu_home": round(mu_home, 2),
        "mu_away": round(mu_away, 2),
        "mu_total": round(mu_total, 2),
    }


def predict_match(home_team_stats, away_team_stats, total_line=220.5):
    home_off_rtg = home_team_stats.get("off_rtg", 110.0)
    away_off_rtg = away_team_stats.get("off_rtg", 110.0)
    pace_home = home_team_stats.get("pace", 100.0)
    pace_away = away_team_stats.get("pace", 100.0)
    pace = (pace_home + pace_away) / 2.0
    return calculate_probabilities(home_off_rtg, away_off_rtg, pace, total_line=total_line)


def extract_team_stats_from_api(fixture_data, team_stats_response):
    if not team_stats_response:
        return {"off_rtg": 110.0, "pace": 100.0}
    try:
        stats = team_stats_response[0] if isinstance(team_stats_response, list) and len(team_stats_response) > 0 else team_stats_response
        ppg = stats.get("points", {}).get("for", {}).get("average", {}).get("total", 110.0)
        off_rtg = float(ppg)
        return {
            "off_rtg": max(90.0, min(130.0, off_rtg)),
            "pace": 100.0,
        }
    except Exception as e:
        print(f"[WARN] Could not extract basketball team stats: {e}")
        return {"off_rtg": 110.0, "pace": 100.0}
