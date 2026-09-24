"""Поток входящих событий: он попадает в тот же публичный репозиторий, что корпус.

Значит, к нему те же требования: реквизиты заведомо фиктивны, сборка побайтово
воспроизводима, письма с вложениями — тоже (у multipart граница по умолчанию случайная,
и без явной границы поток разъезжался бы на каждой сборке).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from rodos_corpus.build import render_all
from rodos_corpus.lint import check_sources
from rodos_corpus.paths import stream_root
from rodos_corpus.render import render
from rodos_corpus.source import SourceDoc, load_all, validate

EXPECTED = 13
WITH_ATTACHMENTS = {"EVT-2026-0007", "EVT-2026-0008", "EVT-2026-0009"}
# Ловушки помечены полем `contains`, а не заголовком: потребитель читает заголовок,
# и подсказка в нём обесценила бы ловушку.
WITH_TRAPS = {"EVT-2026-0001", "EVT-2026-0002", "EVT-2026-0003",
              "EVT-2026-0004", "EVT-2026-0005", "EVT-2026-0006"}


@pytest.fixture(scope="module")
def stream_docs() -> list[SourceDoc]:
    return load_all(stream_root())


def test_stream_loads(stream_docs: list[SourceDoc]) -> None:
    assert len(stream_docs) == EXPECTED


def test_one_quote_request_is_free_of_traps(stream_docs: list[SourceDoc]) -> None:
    """Поток обязан содержать хотя бы один запрос КП, который проходит до конца.

    Скидка требует одновременно действующего договора, категории A или B и предоплаты
    не меньше 30 %, и из восьми договоров мира это сочетание даёт только KMP-2025/02.
    Пока такого дела не было, все шесть запросов оказывались ловушками, и сквозной
    путь показать было нечем.
    """
    quotes = [doc for doc in stream_docs if doc.card.get("doc_type") == "quote_request"]
    clean = [doc for doc in quotes if not doc.card.get("contains")]
    assert [doc.doc_id for doc in clean] == ["EVT-2026-0010"]
    assert {doc.doc_id for doc in quotes if doc.card.get("contains")} == WITH_TRAPS


def test_every_event_is_valid(stream_docs: list[SourceDoc]) -> None:
    problems = [problem for doc in stream_docs for problem in validate(doc)]
    assert problems == []


def test_requisites_are_fictitious() -> None:
    """Линтер обязан покрывать поток, а не только корпус: настоящий ИНН в письме
    контрагента ничем не лучше настоящего ИНН в договоре."""
    assert check_sources(stream_root()) == []


def test_attachments_are_attached(stream_docs: list[SourceDoc]) -> None:
    by_id = {doc.doc_id: doc for doc in stream_docs}
    for doc_id in WITH_ATTACHMENTS:
        card = by_id[doc_id].card
        assert card.get("attachments"), f"{doc_id}: в карточке нет вложений"
        stored = yaml.safe_load(
            (stream_root() / "cards" / f"{doc_id}.yaml").read_text(encoding="utf-8"))
        body = (stream_root().parent / str(stored["rendered"])).read_bytes()
        assert b"Content-Disposition: attachment" in body, f"{doc_id}: вложение не приложено"


def test_multipart_boundary_is_stable(tmp_path: Path) -> None:
    """Повторный рендеринг обязан дать те же байты, включая границу multipart."""
    docs = {doc.doc_id: doc for doc in load_all(stream_root())}
    doc = docs["EVT-2026-0007"]
    digests = set()
    for attempt in ("first", "second"):
        target = tmp_path / attempt
        (target / "rendered" / "finance").mkdir(parents=True, exist_ok=True)
        (target / "cards").mkdir(parents=True, exist_ok=True)
        # вложение обязано существовать рядом — рендерим его первым
        for attached in doc.card["attachments"]:
            render_all(None, attached, stream_root())
        source = stream_root() / "rendered" / "finance" / f"{doc.card['attachments'][0]}.docx"
        (target / "rendered" / "finance" / source.name).write_bytes(source.read_bytes())
        path, _ = render(doc, target)
        digests.add(hashlib.sha256(path.read_bytes()).hexdigest())
    assert len(digests) == 1, "письмо с вложением рендерится по-разному"


def test_traps_are_labelled_outside_the_title(stream_docs: list[SourceDoc]) -> None:
    """Признак ловушки живёт в поле `contains`, а не в заголовке: заголовок читает
    любой потребитель, и подсказка в нём обесценивает ловушку."""
    labelled = {doc.doc_id: doc.card.get("contains") or [] for doc in stream_docs}
    assert "prompt_injection" in labelled["EVT-2026-0005"]
    for doc in stream_docs:
        title = str(doc.card["title"]).lower()
        for word in ("инъекц", "несуществующ", "посторонн", "просроч"):
            assert word not in title, f"{doc.doc_id}: заголовок выдаёт ловушку"


def test_subject_folding_is_pinned() -> None:
    """Сворачивание длинных заголовков писем — источник недетерминизма уровня патча Python.

    Между 3.12.3 и 3.12.14 изменилось то, как email-библиотека сворачивает длинный
    заголовок из encoded-word'ов: пробел на месте переноса в одной версии превращается в
    `=?utf-8?q?_?=`, в другой исчезает. Корпус коммитится отрендеренным, поэтому такая
    правка переписывает файлы молча — в CI это выглядело как «разъехались письма», а не
    как «сменился интерпретатор».

    Проверка ловит смену поведения здесь, одной понятной строкой, вместо того чтобы гейт
    воспроизводимости показывал диф по всему потоку. `.python-version` держит патч-версию,
    и uv в CI берёт именно её.
    """
    expected = (
        b"Subject: =?utf-8?b?0JfQsNC/0YDQvtGBINGG0LXQvdGLINC90LAg0LLQsNC7?= 45.67.90, 15\n"
        b" =?utf-8?q?_?==?utf-8?b?0YjRgi4=?="
    )
    body = (stream_root() / "rendered" / "sales" / "EVT-2026-0003.eml").read_bytes()
    start = body.index(b"Subject: ")
    actual = body[start:body.index(b"\nDate:", start)]
    assert actual == expected, (
        "изменилось сворачивание заголовков писем — проверьте версию Python "
        f"(.python-version = {(Path(__file__).parents[1] / '.python-version').read_text().strip()})"
    )
