"""Мир должен быть согласован и заведомо фиктивен — иначе корпус нельзя публиковать."""

from rodos_corpus.lint import check
from rodos_corpus.world import World


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


def test_service_role_is_not_a_person() -> None:
    # Субъект агента (rodos-agent 05 A-240): читает под своим ключом, но не подписывает и не согласует.
    world = World.load()
    roles = world.by_key("roles")
    assert roles["agent_service"]["kind"] == "service"
    assert roles["agent_service"]["approves"] == []
    assert not [p for p in world.people if p.get("role") == "agent_service"]
    world.roles.append({"key": "bot", "title": "Бот", "kind": "robot", "approves": []})
    assert check(world) == ["roles/bot: неизвестный вид роли «robot»"]
