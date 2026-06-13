# Provider Operational Table

Updated 2026-06-13T13:18:26 UTC. TheStatsAPI now ACTIVE.

| Source | Plan | Key | Integ | Extract% | Q | Role | Decision |
|---|---|---|---|---|---|---|---|
| TheStatsAPI | stats_growth_trial | ✓ | yes | 75% | A | PRIMARY shot-level xG (per-shot coords) + PRIMARY odds (market baseline). Team-xG shares upstream w/ Highlightly. | integrate now |
| API-Football | FREE | ✓ | yes | 90% | B | PRIMARY live score/events/lineups | keep |
| Highlightly | BASIC | ✓ | yes | 65% | A | Team-level xG/stats (same upstream as TSA) | keep |
| football-data.org | FREE | ✓ | yes | 95% | B | Standings/scorers/fixtures | keep |
| OpenFootball | open | — | fallback | 30% | C | Fallback scores | keep |
| martj42 results | open | — | yes | 90% | B | Historical Elo/backtest base (31,975 matches 1990-2025) | keep |
| StatsBomb Open | open | — | partial | 40% | B | Style features 30/48 teams | defer |
| scikit-learn | pkg | n/a | yes | 100% | — | ML logistic 1X2 + isotonic (gate PASSED) | integrated |
| statsmodels | pkg | n/a | no | 0% | — | GLM/Poisson goal model (available) | probe |
| penaltyblog | pkg | n/a | no | 0% | — | Dixon-Coles football models (available) | probe |
| soccerdata | pkg | n/a | no | 0% | — | FBref/Understat/Sofascore access | defer |
| TheSportsDB | free | ✓ | no | 0% | C | metadata/logos only | reject |
| ScoreBat | paid | — | no | 0% | D | video highlights only | reject |
| LightGBM/XGBoost/CatBoost | — | n/a | no | 0% | — | gradient boosting | reject |

## Source priority (live)
1. TheStatsAPI shot-level xG + odds  2. Highlightly team xG  3. API-Football live/events/lineups  4. football-data.org standings  5. OpenFootball fallback
