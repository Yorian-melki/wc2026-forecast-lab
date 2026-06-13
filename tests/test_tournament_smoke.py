from wc2026.tournament import run_tournament_to_disk


def test_tournament_smoke(tmp_path):
    artifacts = run_tournament_to_disk(iterations=50, seed=42, out_dir=tmp_path)
    assert not artifacts.summary.empty
    assert (tmp_path / 'summary.csv').exists()
    assert (tmp_path / 'summary.json').exists()
