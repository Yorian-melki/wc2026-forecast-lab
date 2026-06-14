# Run Tests
```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q        # expect: 571 passed
PYTHONPATH=src .venv/bin/python -m py_compile app.py       # dashboard compiles
```
AppTest every Streamlit page (catches runtime crashes pytest misses) — snippet in
`docs/FUTURE_AGENT_START_HERE.md`. ALWAYS run AppTest after editing app.py.
