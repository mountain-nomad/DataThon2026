"""Legal basis of a violation: specialist rule -> violation type (T) -> clauses (R) -> sources.

Data comes from two files the team maintains:
- LEGAL_MAPPING_FILE (fortebank_violation_legal_mapping_updated.yaml): sources, clauses (rules),
  violation types, severity levels and `scenario_rule_map` (specialist rule_id -> type), which
  is the primary key;
- CROSSWALK_FILE (specialist_crosswalk.yaml): the draft fallback for rules the map doesn't list.
Nothing is inferred: an unmapped rule gets no legal basis.

Enforced from the mapping: `max_severity` caps the model's level ("warning" < "violation") and a
type with `show_source: false` (or a level that says so) gets no clauses and no "Источник" line.
"""

import logging
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import yaml

log = logging.getLogger(__name__)

NOT_BINDING = {"not_a_government_normative_legal_act"}
SEVERITY_RANK = {"warning": 0, "violation": 1}
# Levels with no confirmed public norm; the mapping's `unsourced` level applies to them.
UNSOURCED = {"no_confirmed_public_norm"}


def _min_severity(*levels: str | None) -> str:
    known = [lv for lv in levels if lv in SEVERITY_RANK]
    return min(known, key=SEVERITY_RANK.get) if known else "violation"


def _clean_url(url: str) -> str:
    """Drop tracking parameters (utm_*) from a source link."""
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if not k.startswith("utm_")]
    return urlunsplit(parts._replace(query=urlencode(query)))


def _read(path: Path) -> dict:
    if not path.exists():
        log.warning("No file at %s; violations get no legal basis", path)
        return {}
    return yaml.safe_load(path.read_text()) or {}


class LegalIndex:
    def __init__(self, mapping: dict, crosswalk: dict) -> None:
        self.sources = {
            sid: {
                "source_id": sid,
                "title": s.get("title", sid),
                "url": _clean_url(s.get("alternate_url") or s.get("url") or ""),
                "binding": s.get("binding") is not False
                and s.get("normative_status") not in NOT_BINDING,
                "official": bool(s.get("official")),
                "text_verified": bool(s.get("text_verified")),
                "citation_title": s.get("citation_title") or s.get("title", sid),
            }
            for sid, s in (mapping.get("sources") or {}).items()
        }
        self.rules = {r["rule_id"]: r for r in mapping.get("rules") or []}
        self.types = {t["type_id"]: t for t in mapping.get("violation_types") or []}
        self.levels = mapping.get("severity_levels") or {}
        self.scenario_map = (mapping.get("scenario_rule_map") or {}).get("map") or {}
        self.crosswalk = crosswalk.get("specialist_rules") or {}

    def _type_entry(
        self, rule_id: str | None, type_hint: str | None
    ) -> tuple[str | None, dict, str | None]:
        """(type_id, entry, the scenario map's own max_severity for this rule)."""
        if type_hint in self.types:  # the analyzer may name the type directly ("T10")
            return type_hint, self.types[type_hint], None
        mapped = self.scenario_map.get(rule_id) if rule_id else None
        if mapped and mapped.get("type_id") in self.types:
            return mapped["type_id"], self.types[mapped["type_id"]], mapped.get("max_severity")
        target = self.crosswalk.get(rule_id) if rule_id else None
        if isinstance(target, str):
            return (target, self.types[target], None) if target in self.types else (None, {}, None)
        if isinstance(target, dict):
            return None, target, None
        return None, {}, None

    def resolve(self, rule_id: str | None, type_hint: str | None = None) -> dict | None:
        """The legal basis for a specialist result, or None if it isn't mapped."""
        type_id, entry, map_severity = self._type_entry(rule_id, type_hint)
        if not entry:
            return None
        status = entry.get("mapping_status")
        level = self.levels.get("unsourced" if status in UNSOURCED else status) or {}
        max_severity = _min_severity(
            map_severity, entry.get("max_severity"), level.get("max_severity")
        )
        show_source = entry.get("show_source", True) is not False and (
            level.get("show_source", True) is not False
        )
        clauses = []
        for rid in (entry.get("rule_ids") or []) if show_source else []:
            rule = self.rules.get(rid)
            if not rule or rule.get("show_in_api_output") is False:
                continue
            source = self.sources.get(rule.get("source_id"), {})
            clauses.append(
                {
                    "rule_id": rid,
                    "clause": rule.get("clause"),
                    "summary": rule.get("summary_ru"),
                    "human_verified": bool(rule.get("human_verified")),
                    "text_verified": bool(rule.get("text_verified")),
                    "qualifier": rule.get("qualifier_ru"),
                    "binding": rule.get("binding") is not False and source.get("binding", True),
                    "source": source,
                }
            )
        return {
            "type_id": type_id,
            "name": entry.get("name_ru"),
            "observable_cue": entry.get("observable_cue_ru"),
            "mapping_status": status,
            "max_severity": max_severity,
            "show_source": show_source,
            "limitations": entry.get("limitations_ru"),
            "rules": clauses,
        }


def citation(basis: dict) -> str:
    """One line for the API description: the clauses grouped by source, with links."""
    by_source: dict[str, list[str]] = {}
    sources: dict[str, dict] = {}
    if basis.get("show_source") is False:
        return ""
    for c in basis["rules"]:
        source = c["source"]
        if not (
            c.get("binding", True)
            and source.get("binding")
            and source.get("official")
            and source.get("text_verified")
            and c.get("text_verified")
        ):
            continue
        sid = c["source"].get("source_id", "")
        by_source.setdefault(sid, []).append(c["clause"])
        sources[sid] = c["source"]
    parts = []
    for sid, clauses in by_source.items():
        s = sources[sid]
        text = f"{s.get('citation_title') or s.get('title', sid)}, {'; '.join(clauses)}"
        if s.get("url"):
            text += f" ({s['url']})"
        if not s.get("binding", True):
            text += " — вспомогательный образец, не НПА"
        parts.append(text)
    return "Источник: " + " | ".join(parts) if parts else ""


def load_legal(mapping_file: Path, crosswalk_file: Path) -> LegalIndex:
    return LegalIndex(_read(mapping_file), _read(crosswalk_file))
