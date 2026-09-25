"""Реестр бизнес-правил: структура обязана быть верной всегда.

Полнота покрытия (два свидетельства на правило) набирается документами и проверяется
`rodos-corpus rules --check`; здесь фиксируется то, что должно держаться на каждом коммите —
пункт существует в регламенте, документ-свидетельство существует, регламент не подтверждает себя сам.
"""

from __future__ import annotations

from rodos_corpus.rules import MIN_EVIDENCE, check, load


def test_register_is_structurally_valid() -> None:
    assert check(require_min=False) == []


def test_every_rule_has_an_id_and_a_question() -> None:
    rules = load()
    assert rules, "реестр пуст"
    assert len({rule["id"] for rule in rules}) == len(rules), "идентификаторы правил повторяются"
    for rule in rules:
        assert rule.get("questions"), f"{rule['id']}: правило ни одним вопросом сценария не спрашивается"
        assert rule.get("statement"), f"{rule['id']}: нет текста пункта"


def test_every_rule_is_covered_by_two_documents() -> None:
    """Требование оператора: у каждого правила не меньше двух документов о его исполнении.

    Здесь не «порог, который можно поднять», а полное покрытие: оно достигнуто, и новое правило
    без двух свидетельств должно валить сборку сразу, а не накапливаться до следующей ревизии.
    """
    assert check() == []


def test_coverage_is_counted_over_distinct_documents() -> None:
    """Дважды названный один документ — одно свидетельство; иначе порог обходится опечаткой."""
    for rule in load():
        evidence = rule.get("evidence") or []
        assert len(set(evidence)) >= MIN_EVIDENCE, f"{rule['id']}: {evidence}"
