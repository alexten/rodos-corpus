"""Бизнес-правила и свидетельства их исполнения (`world/rules.yaml`).

Правило записано в регламенте; свидетельство — артефакт процесса по конкретному делу. Требование
оператора: у каждого правила не меньше двух свидетельств. Одно свидетельство можно сочинить под
правило, два показывают, что правило действительно живёт в документообороте предприятия.

Проверка намеренно не пытается угадать исполнение по тексту: регулярное выражение путает пересказ
правила с его применением, а в корпусе почти нет ссылок на номера пунктов. Поэтому соответствие
авторское, а код проверяет то, что проверяется точно: пункт существует в регламенте, документ
существует, свидетельств не меньше двух, и регламент не назначен свидетельством сам себе.
"""

from __future__ import annotations

import re
from typing import Any

import yaml

from .paths import cards_root, source_root, stream_root, world_root

MIN_EVIDENCE = 2


def load() -> list[dict[str, Any]]:
    loaded: list[dict[str, Any]] = yaml.safe_load((world_root() / "rules.yaml").read_text(encoding="utf-8"))
    return loaded


def _clause_present(body: str, clause: str) -> bool:
    """Пункт — либо нумерованный абзац «2.1. …», либо заголовок раздела «## 2. …»."""
    escaped = re.escape(clause)
    return bool(re.search(rf"^{escaped}\.\s", body, re.M) or re.search(rf"^#+\s*{escaped}\.", body, re.M))


def _doc_ids() -> set[str]:
    ids = {path.stem for path in cards_root().glob("*.yaml")}
    ids |= {path.stem for path in (stream_root() / "cards").glob("*.yaml")}
    return ids


def _sources() -> dict[str, str]:
    texts: dict[str, str] = {}
    for root in (source_root(), stream_root() / "source"):
        for path in root.rglob("*"):
            if path.is_file():
                doc_id = path.stem.replace(".table", "")
                texts.setdefault(doc_id, path.read_text(encoding="utf-8", errors="ignore"))
    return texts


def check(require_min: bool = True) -> list[str]:
    """`require_min=False` — только структура реестра: пункт есть, документ есть, не сам себе.

    Разделено потому, что структура обязана быть верной всегда, а полнота покрытия набирается
    документами постепенно. Гейт на полноту включается в CI, когда покрытие дойдёт до всех правил;
    держать его красным на main — способ перестать его замечать.
    """
    problems: list[str] = []
    rules = load()
    known = _doc_ids()
    texts = _sources()
    seen: set[str] = set()

    for rule in rules:
        rid = str(rule.get("id") or "<без id>")
        if rid in seen:
            problems.append(f"{rid}: правило объявлено дважды")
        seen.add(rid)

        document = str(rule.get("document", ""))
        clause = str(rule.get("clause", ""))
        body = texts.get(document)
        if body is None:
            problems.append(f"{rid}: регламента «{document}» нет в корпусе")
        elif not _clause_present(body, clause):
            problems.append(f"{rid}: пункта {clause} нет в тексте «{document}»")

        evidence = list(rule.get("evidence") or [])
        for doc_id in evidence:
            if doc_id not in known:
                problems.append(f"{rid}: свидетельства «{doc_id}» нет в корпусе")
            if doc_id == document:
                problems.append(f"{rid}: регламент назначен свидетельством сам себе")
        if require_min and len(set(evidence)) < MIN_EVIDENCE:
            problems.append(
                f"{rid}: свидетельств {len(set(evidence))}, нужно {MIN_EVIDENCE} — "
                f"{'нет ни одного' if not evidence else 'есть только ' + ', '.join(evidence)}"
            )
    return problems


def main(check_only: bool = False) -> int:
    problems = check()
    rules = load()
    covered = sum(1 for rule in rules if len(set(rule.get("evidence") or [])) >= MIN_EVIDENCE)
    print(f"правил: {len(rules)}, покрыто двумя свидетельствами: {covered}")
    for problem in problems:
        print(f"  {problem}")
    if problems:
        print(f"\nпроблем: {len(problems)}")
        return 1
    print("каждое правило подтверждено не менее чем двумя документами")
    return 0
