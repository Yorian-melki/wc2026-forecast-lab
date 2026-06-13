from pathlib import Path


def test_dashboard_files_exist():
    assert Path('app.py').exists()
    assert Path('scripts/run_dashboard.sh').exists()
