# Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Dashboard shows old content | Streamlit cache / stale process | `pkill -f "streamlit run app.py"`, relaunch; hard-refresh browser |
| `NameError: matchId` | `{var}` inside an f-string markdown | escape as `{{var}}` or drop the f-prefix |
| `update_layout() got multiple values for 'xaxis'` | passing `xaxis=` AND `**plotly_layout()` (which sets xaxis) | put the override inside `plotly_layout(xaxis=...)` |
| Live Standings shows "SNAPSHOT" | no `API_FOOTBALL_KEY` in `.env` | add the key, restart |
| A finished match appears under "Upcoming" | stale `upcoming_today` in json | already filtered at render; prune in `merge_and_persist` for a full fix |
| Maturity shows 5.25 | reading `global_maturity_score.json` (legacy) | code now prefers `final_maturity_score_v6.json` |
| A page crashes in browser but pytest is green | pytest doesn't render pages | run AppTest across all pages (see FUTURE_AGENT_START_HERE) |
| Push fails "could not resolve host" | transient sandbox network | retry `git push` |
