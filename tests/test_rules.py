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


def test_coverage_does_not_regress() -> None:
    """Покрытие может только расти. Число поднимается вместе с добавленными документами."""
    covered = sum(1 for rule in load() if len(set(rule.get("evidence") or [])) >= MIN_EVIDENCE)
    assert covered >= 8, f"покрытых правил стало меньше: {covered}"
