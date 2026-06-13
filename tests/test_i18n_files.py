from pathlib import Path
import json
import ast


def test_i18n_files_exist():
    assert Path('ui/i18n/en.json').exists()
    assert Path('ui/i18n/fr.json').exists()


def test_i18n_loadable():
    for p in [Path('ui/i18n/en.json'), Path('ui/i18n/fr.json')]:
        data = json.loads(p.read_text(encoding='utf-8'))
        assert 'sidebar' in data
        assert 'pages' in data
        assert 'metrics' in data


def test_app_compiles():
    source = Path('app.py').read_text(encoding='utf-8')
    ast.parse(source)
