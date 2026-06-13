from wc2026.data_loader import load_groups, load_teams, validate_data
from wc2026.bracket import enumerate_all_third_place_mappings


def test_validate_data():
    validate_data()
    assert len(load_teams()) == 48
    assert len(load_groups()) == 12


def test_third_place_mapping_count_and_validity():
    rows = enumerate_all_third_place_mappings()
    assert len(rows) == 495
    for row in rows:
        used = {row[s] for s in ['1A', '1B', '1D', '1E', '1G', '1I', '1K', '1L']}
        assert len(used) == 8
