"""Мир должен быть согласован и заведомо фиктивен — иначе корпус нельзя публиковать."""

from rodos.corpus.lint import check
from rodos.corpus.world import World


def test_world_loads_and_is_consistent() -> None:
    world = World.load()
    assert check(world) == []


def test_world_has_expected_scale() -> None:
    world = World.load()
    assert len(world.sites) == 3
    assert len(world.workshops) == 6
    assert len(world.parts) >= 40
    assert len(world.counterparties_flat) >= 20
    assert len(world.contracts) >= 18


def test_assemblies_reference_existing_parts() -> None:
    world = World.load()
    parts = world.by_key("parts")
    assemblies = [part for part in world.parts if part.get("components")]
    assert assemblies, "в мире должны быть сборочные единицы"
    for assembly in assemblies:
        for component in assembly["components"]:
            assert component in parts
