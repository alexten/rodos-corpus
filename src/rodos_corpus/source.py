"""Исходники документов корпуса: разбор файлов corpus/source/**.

Документ описывается одним файлом:

* `<doc_id>.md` — YAML-шапка (карточка документа) и тело в ограниченном markdown;
* `<doc_id>.table.yaml` — карточка и описание таблицы, из которой рендерится XLSX;
* `<doc_id>.mail.md` — карточка с полями письма и тело; рендерится в EML.

Карточка — это одновременно метаданные документа и эталон для оценки извлечения (docs/spec/06, §7).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml

REQUIRED = ("doc_id", "doc_type", "title", "org_unit", "spaces", "confidentiality", "status", "format")
FORMATS = {"docx", "pdf", "xlsx", "eml", "txt", "xml", "pdf_scan"}
STATUSES = {"active", "superseded", "retracted", "draft"}
CONFIDENTIALITY = {"public", "internal", "dsp"}
CHANNELS = {"dropdir", "edo", "mail", "npa", "manual"}
FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n?(.*)\Z", re.S)


def corpus_root() -> Path:
    return Path(__file__).resolve().parents[3] / "corpus"


@dataclass(frozen=True)
class SourceDoc:
    """Исходник одного документа: карточка, тело и путь."""

    path: Path
    card: dict[str, Any]
    body: str
    table: dict[str, Any] | None = field(default=None)

    @property
    def doc_id(self) -> str:
        return str(self.card["doc_id"])

    @property
    def space(self) -> str:
        """Пространство-владелец — первое в списке ожидаемых."""
        return str(self.card["spaces"][0])

    @property
    def fmt(self) -> str:
        return str(self.card["format"])


def parse(path: Path) -> SourceDoc:
    text = path.read_text(encoding="utf-8")
    if path.name.endswith(".table.yaml"):
        data = yaml.safe_load(text)
        card = dict(data)
        table = card.pop("table")
        return SourceDoc(path=path, card=card, body="", table=table)
    match = FRONT_MATTER.match(text)
    if not match:
        raise ValueError(f"{path}: нет YAML-шапки")
    card = yaml.safe_load(match.group(1)) or {}
    return SourceDoc(path=path, card=card, body=match.group(2).strip() + "\n")


def validate(doc: SourceDoc) -> list[str]:
    """Проверки карточки: без них документ не индексируется (docs/spec/03, §4)."""
    problems: list[str] = []
    card = doc.card
    for field_name in REQUIRED:
        if not card.get(field_name):
            problems.append(f"{doc.path.name}: нет обязательного поля «{field_name}»")
    if card.get("format") not in FORMATS | {None}:
        problems.append(f"{doc.path.name}: неизвестный формат «{card.get('format')}»")
    if card.get("status") not in STATUSES | {None}:
        problems.append(f"{doc.path.name}: неизвестный статус «{card.get('status')}»")
    if card.get("confidentiality") not in CONFIDENTIALITY | {None}:
        problems.append(f"{doc.path.name}: неизвестный гриф «{card.get('confidentiality')}»")
    if (channel := card.get("channel")) and channel not in CHANNELS:
        problems.append(f"{doc.path.name}: неизвестный канал «{channel}»")
    if card.get("status") == "superseded" and not card.get("superseded_by"):
        problems.append(f"{doc.path.name}: замещённый документ без ссылки superseded_by")
    # Отменённый документ обязан говорить, чем он отменён: иначе ответ «документ отменён» некуда раскрыть,
    # а замолчавший документ без объяснения выглядит как потеря, а не как решение.
    if card.get("status") == "retracted" and not card.get("retracted_by"):
        problems.append(f"{doc.path.name}: отменённый документ без ссылки retracted_by")
    for name in ("approved_at", "effective_from", "effective_to"):
        value = card.get(name)
        if value is not None and not isinstance(value, date):
            problems.append(f"{doc.path.name}: поле «{name}» должно быть датой, а не «{value}»")
    if doc.table is None and not doc.body.strip():
        problems.append(f"{doc.path.name}: пустое тело документа")
    return problems


def load_all(root: Path | None = None) -> list[SourceDoc]:
    """Все исходники корпуса, отсортированные по идентификатору."""
    base = (root or corpus_root()) / "source"
    if not base.exists():
        return []
    docs = [parse(path) for path in sorted(base.rglob("*"))
            if path.is_file() and path.suffix in {".md", ".yaml"}]
    return sorted(docs, key=lambda doc: doc.doc_id)
