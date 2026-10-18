"""Validate local ML findings against the fixed, reviewable scenario catalogue."""
from functools import lru_cache
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

@lru_cache(maxsize=1)
def catalog():
    return json.loads((ROOT / 'ml/configs/finding_types.json').read_text())

def require_type(rule_id: str, public_type: str) -> dict:
    value = catalog().get(rule_id)
    if value is None:
        raise ValueError('Unknown rule_id: ' + str(rule_id))
    if value['allows_violation']:
        allowed = ['НАРУШЕНИЕ: ' + value['name_ru'], 'ПРЕДУПРЕЖДЕНИЕ: ' + value['name_ru']]
    else:
        allowed = ['ПРЕДУПРЕЖДЕНИЕ: Не подтверждено — ' + value['name_ru'].lower()]
    if public_type not in allowed:
        raise ValueError('Finding type does not match rule_id: ' + rule_id)
    return value
