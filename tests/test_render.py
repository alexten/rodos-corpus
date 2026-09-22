"""Рендеринг корпуса: детерминизм и структура документа.

Главная проверка здесь — побайтовое совпадение при повторной сборке. Без неё хеш документа меняется
сам по себе, и сравнивать прогоны оценки между собой становится нельзя (docs/spec/06, §3).
"""

from __future__ import annotations

import hashlib

import pytest

from rodos.corpus.render import render
from rodos.corpus.source import corpus_root, load_all

FORMATS = ("docx", "pdf", "xlsx", "eml", "txt", "xml", "pdf_scan")


@pytest.fixture(scope="module")
def docs() -> list:
    loaded = load_all()
    assert loaded, "корпус пуст: выполните `rodos corpus generate`"
    return loaded


@pytest.fixture(scope="module")
def by_format(docs: list) -> dict:
    """По одному документу каждого формата — проверяем все ветки рендеринга, а не одну."""
    chosen: dict[str, object] = {}
    for doc in docs:
        chosen.setdefault(doc.fmt, doc)
    return chosen


@pytest.mark.parametrize("fmt", FORMATS)
def test_render_is_byte_stable(by_format: dict, tmp_path, fmt: str) -> None:
    doc = by_format.get(fmt)
    assert doc is not None, f"в корпусе нет ни одного документа формата {fmt}"

    first, _ = render(doc, tmp_path / "one")
    second, _ = render(doc, tmp_path / "two")
    digest = hashlib.sha256(first.read_bytes()).hexdigest()
    assert digest == hashlib.sha256(second.read_bytes()).hexdigest(), \
        f"{doc.doc_id}: повторная сборка дала другой файл"


def test_scan_has_no_text_layer(by_format: dict, tmp_path) -> None:
    """Скан обязан быть картинкой: карточка есть, содержимого нет."""
    doc = by_format["pdf_scan"]
    target, _ = render(doc, tmp_path)
    payload = target.read_bytes()
    assert b"/Image" in payload
    assert b"/Font" not in payload, f"{doc.doc_id}: у скана не должно быть текстового слоя"


def test_every_document_has_a_card(docs: list) -> None:
    """Карточка — эталон для оценки извлечения; документ без неё не участвует в оценке."""
    cards = {path.stem for path in (corpus_root() / "cards").glob("*.yaml")}
    missing = sorted({doc.doc_id for doc in docs} - cards)
    assert not missing, f"нет эталонных карточек: {missing[:10]}"
