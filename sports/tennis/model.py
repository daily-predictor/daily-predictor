#!/usr/bin/env python3
"""Tennis prediction model using Markov chain."""
from functools import lru_cache
from scipy.stats import norm, binom


def game_win_prob(p):
    q = 1 - p
    if p == 0.5:
        return 0.5
    numerator = (p ** 4) * (1 + 4 * q + 10 * (q ** 2))
    denominator = 1 - 2 * p * q
    return numerator / denominator


@lru_cache(maxsize=1000)
def set_win_prob(p_serve, p_return, target_games=6):
    g_serve = game_win_prob(p_serve)
    g_return = game_win_prob(p_return)
    expected_games = 6 * g_serve + 6 * (1 - g_return)
    variance = 6 * g_serve * (1 - g_serve) + 6 * g_return * (1 - g_return)
    p_set = norm.cdf((expected_games - 6.5) / (variance ** 0.5 + 0.001))
    return max(0.01, min(0.99, p_set))


def match_win_prob(p_serve, p_return, best_of=3):
    p_set = set_win_prob(p_serve, p_return)
    if best_of == 3:
        p_2_0 = p_set ** 2
        p_2_1 = 2 * (p_set ** 2) * (1 - p_set)
        return p_2_0 + p_2_1, p_2_0
    else:
        p_match = 1 - binom.cdf(2, 5, p_set)
        p_3_0 = p_set ** 3
        return p_match, p_3_0


def calculate_probabilities(p_serve_a, p_return_a, p_serve_b, p_return_b, best_of=3):
    p_match_a, p_straight_a = match_win_prob(p_serve_a, p_return_a, best_of)
    p_match_b, p_straight_b = match_win_prob(p_serve_b, p_return_b, best_of)
    total = p_match_a + p_match_b
    if total > 0:
        p_match_a_norm = p_match_a / total
        p_match_b_norm = p_match_b / total
    else:
        p_match_a_norm = 0.5
        p_match_b_norm = 0.5
    sets_handicap = round((p_match_a_norm - 0.5) * 4, 1)
    return {
        "p_home": round(p_match_a_norm, 4),
        "p_away": round(p_match_b_norm, 4),
        "p_win_2_0": round(p_straight_a, 4),
        "sets_handicap": sets_handicap,
        "fair_odds_home": round(1.0 / p_match_a_norm, 2) if p_match_a_norm > 0 else 999,
        "fair_odds_away": round(1.0 / p_match_b_norm, 2) if p_match_b_norm > 0 else 999,
    }


def predict_match(player_a_stats, player_b_stats, best_of=3):
    return calculate_probabilities(
        player_a_stats.get("serve_win_pct", 0.65),
        player_a_stats.get("return_win_pct", 0.35),
        player_b_stats.get("serve_win_pct", 0.65),
        player_b_stats.get("return_win_pct", 0.35),
        best_of=best_of
    )


def extract_player_stats_from_api(fixture_data, player_stats_response):
    if not player_stats_response:
        return {"serve_win_pct": 0.65, "return_win_pct": 0.35}
    try:
        stats = player_stats_response[0] if isinstance(player_stats_response, list) and len(player_stats_response) > 0 else player_stats_response
        serve_won = stats.get("statistics", {}).get("serve", {}).get("points_won", {}).get("percentage", 65)
        return_won = stats.get("statistics", {}).get("return", {}).get("points_won", {}).get("percentage", 35)
        return {
            "serve_win_pct": float(serve_won) / 100.0,
            "return_win_pct": float(return_won) / 100.0,
        }
    except Exception as e:
        print(f"[WARN] Could not extract tennis player stats: {e}")
        return {"serve_win_pct": 0.65, "return_win_pct": 0.35}
