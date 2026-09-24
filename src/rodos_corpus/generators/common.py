"""Общее для генераторов: запись исходников документов."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from rodos_corpus.source import corpus_root


def write_source(space: str, doc_id: str, card: dict[str, Any], body: str, root: Path | None = None) -> Path:
    """Пишет corpus/source/<space>/<doc_id>.md с YAML-шапкой."""
    base = (root or corpus_root()) / "source" / space
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{doc_id}.md"
    front = yaml.dump(card, allow_unicode=True, sort_keys=False).strip()
    path.write_text(f"---\n{front}\n---\n\n{body.strip()}\n", encoding="utf-8")
    return path


def write_table_source(space: str, doc_id: str, card: dict[str, Any], table: Any,
                       root: Path | None = None) -> Path:
    """Пишет corpus/source/<space>/<doc_id>.table.yaml для XLSX-документа."""
    base = (root or corpus_root()) / "source" / space
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{doc_id}.table.yaml"
    payload = dict(card)
    payload["table"] = table
    path.write_text(yaml.dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path
