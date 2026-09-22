"""Загрузка модели мира из world/*.yaml.

Мир — источник истины для демо-корпуса: из него порождаются документы и выводятся эталонные ответы
(см. docs/spec/06-corpus.md). Здесь только чтение и индексация по ключам; проверки — в lint.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any

import yaml

FILES = (
    "sites", "workshops", "equipment", "materials", "parts", "counterparties",
    "contracts", "products", "systems", "roles", "people", "calendar",
)


def default_root() -> Path:
    """Каталог world/ в корне репозитория."""
    return Path(__file__).resolve().parents[3] / "world"


@dataclass(frozen=True)
class World:
    """Справочники мира. Списочные файлы — списки словарей, остальные — словари."""

    data: dict[str, Any]

    @classmethod
    def load(cls, root: Path | None = None) -> World:
        root = root or default_root()
        missing = [name for name in FILES if not (root / f"{name}.yaml").exists()]
        if missing:
            raise FileNotFoundError(f"нет файлов мира: {', '.join(missing)} (каталог {root})")
        return cls({name: yaml.safe_load((root / f"{name}.yaml").read_text(encoding="utf-8"))
                    for name in FILES})

    def __getattr__(self, name: str) -> Any:
        if name in self.data:
            return self.data[name]
        raise AttributeError(name)

    @cached_property
    def materials_flat(self) -> list[dict[str, Any]]:
        """Стали, инструмент и расходники одним списком — у всех есть key."""
        return [item for group in self.data["materials"].values() for item in group]

    @cached_property
    def counterparties_flat(self) -> list[dict[str, Any]]:
        return [item for group in self.data["counterparties"].values() for item in group]

    def by_key(self, collection: str) -> dict[str, dict[str, Any]]:
        """Индекс записей по полю key (или drawing_no для деталей, no для договоров)."""
        items = {
            "materials": self.materials_flat,
            "counterparties": self.counterparties_flat,
            "products": self.data["products"]["items"],
        }.get(collection, self.data.get(collection))
        if not isinstance(items, list):
            raise KeyError(f"{collection} не список записей")
        field = {"parts": "drawing_no", "contracts": "number", "products": "sku"}.get(collection, "key")
        return {item[field]: item for item in items}
