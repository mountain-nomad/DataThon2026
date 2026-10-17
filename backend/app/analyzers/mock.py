"""Fake analyzer for wiring and UI work. Its output means nothing about the video.

It imitates the router -> specialists pipeline: picks one or two of the 7 scenarios and returns
one specialist result per scenario. Rule ids and quotes are copied from the specialist prompts'
catalogs; the evidence text is fake and marked [MOCK].
"""

import hashlib
import os
import random
import time

from app.analyzers import AnalysisContext, AnalysisResult, Scenario, SpecialistResult
from app.video import probe_duration

# scenario -> [(type, rule_id, quote)] of the violations its specialist can report
_VIOLATIONS: dict[str, list[tuple[str, str, str]]] = {
    "ENTRY": [
        (
            "client_in_service_zone",
            "s1:L13",
            "Нарушение: клиент заходит в служебную зону на стороне кассира.",
        ),
        (
            "door_left_open",
            "s1:L14",
            "Нарушение: кассир оставляет дверь на своей стороне открытой после входа.",
        ),
        (
            "personal_items_on_desk",
            "s1:L15",
            "Нарушение: кассир кладет личные вещи на рабочий стол.",
        ),
    ],
    # The regulation lists no confirmed violation types for this scenario.
    "COUNTING_DEPOSIT_WITHOUT_CLIENT": [],
    "CLIENT_CASH_DEPOSIT": [
        (
            "no_document_check",
            "s2:L58",
            "Нарушение: кассир принимает деньги клиента без обязательной проверки документа.",
        ),
        (
            "cash_not_in_safe",
            "s2:L59",
            "Нарушение: кассир не помещает принятые деньги клиента в сейф до завершения операции.",
        ),
        (
            "no_banknote_check",
            "s2:L62",
            "Нарушение: кассир пропускает обязательную проверку купюр на подлинность.",
        ),
    ],
    "COUNTING_FROM_SAFE": [
        (
            "safe_left_open",
            "s3:L85",
            "Нарушение: кассир оставляет сейф открытым после извлечения денег и перехода к подсчету.",
        ),
    ],
    "OPENING_A_CASH_BAG": [
        (
            "deposit_without_count",
            "s4:L110",
            (
                "Нарушение: кассир помещает деньги из мешка в сейф без обязательного предварительного "
                "подсчета."
            ),
        ),
    ],
    "RECEIVING_A_BAG_FROM_CLIENT": [
        (
            "bag_without_document_check",
            "s5:L136",
            (
                "Нарушение: кассир принимает мешок от клиента, не выполнив обязательную проверку "
                "документа."
            ),
        ),
    ],
    "EXIT_CLOSING": [
        (
            "equipment_left_on",
            "s7:L182",
            "Нарушение: кассир выходит, оставив компьютер или другие электроприборы включенными.",
        ),
        (
            "key_left_in_safe",
            "s7:L183",
            "Нарушение: кассир выходит, оставив ключ в замочной скважине.",
        ),
        (
            "cash_left_on_desk",
            "s7:L185",
            "Нарушение: кассир оставляет деньги на столе перед уходом.",
        ),
    ],
}


class MockAnalyzer:
    def __init__(self) -> None:
        self.delay_sec = float(os.environ.get("MOCK_DELAY_SEC", "3"))

    def analyze(self, video_path: str, ctx: AnalysisContext) -> AnalysisResult:
        duration = probe_duration(video_path) or 10.0
        # Same file -> same answer, so re-running a video doesn't change the "result".
        with open(video_path, "rb") as f:
            seed = hashlib.sha256(f.read(1 << 20)).hexdigest()
        rng = random.Random(seed)
        scenarios = rng.sample(list(_VIOLATIONS), 2 if rng.random() < 0.4 else 1)
        result = AnalysisResult(
            scenario=Scenario(
                primary=scenarios[0], secondary=scenarios[1] if len(scenarios) > 1 else None
            )
        )
        # Like the real pipeline: router first, then one specialist per scenario, reporting each
        # step. A specialist is skipped when its run wouldn't fit before the deadline.
        step = self.delay_sec / (len(scenarios) + 1)
        time.sleep(step)
        ctx.report(result)
        for s in scenarios:
            if ctx.time_left() < step:
                break
            time.sleep(step)
            result.specialist_results.append(self._specialist(rng, s, duration))
            ctx.report(result)
        return result

    @staticmethod
    def _specialist(rng: random.Random, scenario: str, duration: float) -> SpecialistResult:
        options = _VIOLATIONS[scenario]
        roll = rng.random()
        if not options or roll < 0.3:
            return SpecialistResult(
                scenario=scenario,
                status="no_violation",
                evidence="[MOCK] Операция видна полностью, нарушений не найдено.",
            )
        if roll < 0.45:
            return SpecialistResult(
                scenario=scenario,
                status="insufficient_evidence",
                evidence="[MOCK] Ключевой момент операции вне кадра.",
            )
        kind, rule_id, quote = rng.choice(options)
        start = round(rng.uniform(0.1, 0.75) * duration, 1)
        return SpecialistResult(
            scenario=scenario,
            status="violation",
            type=kind,
            rule_id=rule_id,
            quote=quote,
            evidence=f"[MOCK] Признаки нарушения «{kind}» на кадрах около {start:.1f} с.",
            start_sec=start,
            end_sec=round(min(start + rng.uniform(3, 8), duration), 1),
            confidence=round(rng.uniform(0.55, 0.95), 2),
        )
