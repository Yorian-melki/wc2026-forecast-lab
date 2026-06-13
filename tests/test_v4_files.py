from pathlib import Path
import json


def test_market_sample_exists_and_has_rows():
    path = Path('data/market_odds_sample.csv')
    assert path.exists()
    text = path.read_text(encoding='utf-8').strip().splitlines()
    assert len(text) > 5


def test_v4_i18n_pages_exist():
    for lang in ['en', 'fr']:
        path = Path(f'ui/i18n/{lang}.json')
        data = json.loads(path.read_text(encoding='utf-8'))
        assert 'market' in data['pages']
        assert 'publication' in data['pages']
        assert 'market_csv' in data['sidebar']


def test_publication_docs_exist():
    for path in [
        Path('docs/linkedin_readme_en.md'),
        Path('docs/linkedin_readme_fr.md'),
    ]:
        assert path.exists()
        assert path.read_text(encoding='utf-8').strip()
