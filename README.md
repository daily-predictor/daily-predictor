# Daily Predictor

A sports prediction web app that runs daily at 05:00 UTC, fetches live data, calculates probabilities using exact mathematical formulas (no LLM), and serves predictions via a JSON dashboard.

## Features

- **6 Sports**: Soccer, Basketball, Baseball, Tennis, Hockey, Handball
- **Mathematical Models Only**:
  - Soccer/Hockey/Handball: Poisson distribution (HOME_ADV=1.12)
  - Basketball: Normal distribution (sigma_diff=11, sigma_total=14)
  - Baseball: Bill James Pythagorean + Poisson (exponent=1.82)
  - Tennis: Markov chain recursive game/set/match probabilities
- **Live Data**: The Odds API, API-SPORTS, MLB Stats API
- **EV Calculation**: Compares model fair odds vs market odds
- **Caching**: 1-hour request cache
- **Scheduled Deployment**: Runs automatically via Replit at 05:00 UTC

## Project Structure

```
daily_predictor/
├── main.py                    # HTTP server
├── requirements.txt           # Dependencies
├── .replit                    # Replit config + scheduled deployment
├── sports/
│   ├── soccer/model.py        # Poisson model
│   ├── hockey/model.py        # Poisson model
│   ├── handball/model.py      # Poisson model
│   ├── basketball/model.py    # Normal distribution
│   ├── baseball/model.py      # Pythagorean + Poisson
│   └── tennis/model.py        # Markov chain
├── scripts/
│   ├── fetch_api.py           # API clients with caching
│   └── daily_run.py           # Daily pipeline runner
├── output/                    # JSON predictions per sport per day
└── frontend/
    └── index.html             # Dashboard
```

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/daily-predictor.git
cd daily-predictor
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure API Keys

Set environment variables or create a `.env` file:

```bash
export ODDS_API_KEY="your_odds_api_key"
export API_SPORTS_KEY="your_api_sports_key"
```

- [The Odds API](https://the-odds-api.com) - 500 free requests/month
- [API-SPORTS](https://api-sports.io) - 100 free requests/day
- MLB Stats API - Free, no key required

### 4. Run the Daily Pipeline

```bash
python scripts/daily_run.py
```

Generates prediction JSON files in `/output/{sport}/{YYYY-MM-DD}.json`.

### 5. Start the Web Server

```bash
python main.py
```

Open http://localhost:8080 to view the dashboard.

## Scheduled Deployment (Replit)

1. Import this repository into [Replit](https://replit.com)
2. Add Secrets: `ODDS_API_KEY` and `API_SPORTS_KEY`
3. Configure Scheduled Deployment to run `python scripts/daily_run.py` at **05:00 UTC daily**
4. The `.replit` file is already configured for this

## Mathematical Models

### Soccer / Hockey / Handball (Poisson)

```
lambda_home = home_attack * away_defence * league_avg_goals * HOME_ADV * rest_factor
lambda_away = away_attack * home_defence * league_avg_goals * rest_factor
HOME_ADV = 1.12

P(k; lambda) = exp(-lambda) * lambda^k / k!

P_home_win = sum(i=1..6) sum(j=0..i-1) P(i; lambda_home) * P(j; lambda_away)
P_draw     = sum(i=0..6) P(i; lambda_home) * P(i; lambda_away)
P_away_win = 1 - P_home_win - P_draw
P_over_2.5 = sum(i+j > 2.5) P(i; lambda_home) * P(j; lambda_away)
```

### Basketball (Normal Distribution)

```
mu_home = pace * home_off_rtg / 100
mu_away = pace * away_off_rtg / 100
mu_diff = mu_home - mu_away + 2.5
sigma_diff = 11.0

P_home = Phi(mu_diff / sigma_diff)
P_away = 1 - P_home

Total ~ N(mu_home + mu_away, sigma_total=14)
P_over = 1 - Phi((line - mu_total) / sigma_total)
```

### Baseball (Pythagorean + Poisson)

```
win_pct = RS^1.82 / (RS^1.82 + RA^1.82)

lambda_home = (home_RS_per_game * away_RA_per_game / league_avg) * park_factor
lambda_away = (away_RS_per_game * home_RA_per_game / league_avg) * park_factor
```

### Tennis (Markov Chain)

```
g(p) = p^4 * (1 + 4(1-p) + 10(1-p)^2) / (1 - 2p(1-p))

Recursive set win -> match win (best of 3 or 5)
```

## Output Format

```json
{
  "date": "2026-06-18",
  "sport": "soccer",
  "predictions": [
    {
      "match": "Arsenal vs Chelsea",
      "p_home": 0.54,
      "p_draw": 0.24,
      "p_away": 0.22,
      "ou25_over": 0.48,
      "fair_odds_home": 1.85,
      "market_odds_home": 2.10,
      "ev_home": 0.07
    }
  ],
  "generated_at": "2026-06-18T05:00:00Z"
}
```

## License

MIT
