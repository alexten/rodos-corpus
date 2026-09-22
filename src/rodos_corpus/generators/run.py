"""Запуск всех генераторов корпуса: world → corpus/source/**."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from rodos.corpus.generators import production_docs, tech_cards
from rodos.corpus.world import World

Generator = Callable[..., list[Path]]
ALL: tuple[tuple[str, Generator], ...] = (
    ("tech_cards", tech_cards.generate),
    *((generator.__name__, generator) for generator in production_docs.GENERATORS),
)


def run(names: list[str] | None = None, root: Path | None = None) -> int:
    world = World.load()
    total = 0
    for name, generator in ALL:
        if names and name not in names:
            continue
        written = generator(world, root)
        total += len(written)
        print(f"{name:22s} {len(written):4d}")
    print(f"исходников создано: {total}")
    return 0
