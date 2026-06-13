PYTHON ?= python

install:
	$(PYTHON) -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && pip install -e .

test:
	. .venv/bin/activate && pytest -q

validate:
	. .venv/bin/activate && python -m wc2026.cli validate-data

thirds:
	. .venv/bin/activate && python -m wc2026.cli export-third-place-map --out outputs/generated_third_place_mapping.csv

pairwise:
	. .venv/bin/activate && python -m wc2026.cli precompute-pairwise --iterations 1000000 --jobs 8 --batch-size 50000 --out outputs/pairwise_summary.csv

tournament:
	. .venv/bin/activate && python -m wc2026.cli simulate-tournament --iterations 100000 --seed 20260404 --out-dir outputs/tournament_run
