"""Опись корпуса: идентификатор документа → sha256 отрендеренного файла.

Зачем. Хеш документа — это его идентичность: по нему идёт дедупликация при приёме, он попадает в
эталонную карточку и в отчёт прогона оценки. Пока корпус лежал в одном репозитории с приложением,
«какая версия корпуса» отвечалось коммитом этого репозитория. После выноса в пакет такого ответа
нет, и его нужно дать явно: прогон оценки записывает `CORPUS_VERSION`, и два прогона сравнимы,
только если версия совпала.

`verify()` — дешёвая проверка целостности: потребитель может убедиться, что файлы, которые он
индексирует, те самые, а не пересобранные чем-то по дороге.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from rodos_corpus.paths import cards_root, data_root, stream_root

CORPUS_VERSION = "1.1.0"
MANIFEST_FILE = "MANIFEST.json"


def _card_files() -> list[Path]:
    """Карточки корпуса и потока: опись покрывает и то, и другое."""
    return sorted(cards_root().glob("*.yaml")) + sorted((stream_root() / "cards").glob("*.yaml"))


def build() -> dict[str, Any]:
    """Собрать опись заново по карточкам — источник истины при сборке."""
    entries: dict[str, str] = {}
    for card_path in _card_files():
        card = yaml.safe_load(card_path.read_text(encoding="utf-8"))
        target = data_root() / str(card["rendered"])
        entries[str(card["doc_id"])] = hashlib.sha256(target.read_bytes()).hexdigest()
    return {"version": CORPUS_VERSION, "documents": len(entries), "sha256": entries}


def manifest() -> dict[str, Any]:
    """Опись, как она лежит в пакете."""
    path = data_root() / MANIFEST_FILE
    if not path.exists():
        return build()
    loaded: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def verify() -> list[str]:
    """Расхождения между описью и файлами на диске. Пустой список — всё сходится."""
    recorded = manifest()["sha256"]
    problems: list[str] = []
    seen: set[str] = set()
    for card_path in _card_files():
        card = yaml.safe_load(card_path.read_text(encoding="utf-8"))
        doc_id = str(card["doc_id"])
        seen.add(doc_id)
        target = data_root() / str(card["rendered"])
        if not target.exists():
            problems.append(f"{doc_id}: файла нет — {card['rendered']}")
            continue
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if doc_id not in recorded:
            problems.append(f"{doc_id}: нет в описи")
        elif recorded[doc_id] != actual:
            problems.append(f"{doc_id}: хеш не совпал с описью")
    for doc_id in sorted(recorded.keys() - seen):
        problems.append(f"{doc_id}: есть в описи, но карточки нет")
    return problems


def write() -> int:
    path = data_root() / MANIFEST_FILE
    data = build()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    print(f"{MANIFEST_FILE}: {data['documents']} документов, версия {data['version']}")
    return 0
