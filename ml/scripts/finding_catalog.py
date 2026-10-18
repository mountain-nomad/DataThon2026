"""Fixed public type names, tied to exact regulation quotes and stable rule identifiers."""
from functools import lru_cache
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

@lru_cache(maxsize=1)
def catalog():
    return json.loads((ROOT / 'configs/finding_types.json').read_text())

def entry(rule_id, rule=None):
    value = catalog().get(rule_id)
    if value is None:
        raise ValueError('Unknown finding rule: ' + str(rule_id))
    if rule is not None and value['quote'] != rule['quote']:
        raise ValueError('Finding catalogue differs from regulation: ' + rule_id)
    return value

def allowed_types(rule_id, rule=None):
    value = entry(rule_id, rule)
    if value['allows_violation']:
        return ['НАРУШЕНИЕ: ' + value['name_ru'], 'ПРЕДУПРЕЖДЕНИЕ: ' + value['name_ru']]
    return ['ПРЕДУПРЕЖДЕНИЕ: Не подтверждено — ' + value['name_ru'].lower()]

def canonical_type(rule_id, kind, rule=None):
    allowed = allowed_types(rule_id, rule)
    if kind not in allowed:
        raise ValueError('Type does not match its catalogue rule: ' + str(rule_id))
    return kind
