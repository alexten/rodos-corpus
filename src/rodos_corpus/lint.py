"""Проверки модели мира и корпуса: ссылки разрешаются, реквизиты заведомо фиктивны.

Запуск: rodos corpus lint. Линтер обязан падать до коммита, а не после публикации репозитория.
"""

from __future__ import annotations

import re
from pathlib import Path

from rodos.corpus.world import World

SPACES = {"production", "finance", "sales", "it", "common"}
FAKE_INN = re.compile(r"^00\d{8,10}$")
FAKE_EMAIL = re.compile(r"@[\w.-]*example\.com$")
FAKE_PHONE = re.compile(r"^\+7 \(495\) 000-00-\d\d$")


def check(world: World) -> list[str]:
    """Возвращает список нарушений; пустой список — мир согласован."""
    problems: list[str] = []
    site_keys = set(world.by_key("sites"))
    workshop_keys = set(world.by_key("workshops"))
    equipment_keys = set(world.by_key("equipment"))
    material_keys = set(world.by_key("materials"))
    part_keys = set(world.by_key("parts"))
    counterparty_keys = set(world.by_key("counterparties"))
    contract_numbers = set(world.by_key("contracts"))
    role_keys = set(world.by_key("roles"))

    def ref(where: str, value: str | None, pool: set[str], what: str) -> None:
        if value is not None and value not in pool:
            problems.append(f"{where}: неизвестный {what} «{value}»")

    for shop in world.workshops:
        ref(f"workshops/{shop['key']}", shop.get("site"), site_keys, "site")
        ref(f"workshops/{shop['key']}", shop.get("head_role"), role_keys, "head_role")
        for item in shop.get("equipment", []):
            ref(f"workshops/{shop['key']}", item, equipment_keys, "станок")

    for machine in world.equipment:
        ref(f"equipment/{machine['key']}", machine.get("workshop"), workshop_keys, "цех")

    for material in world.materials_flat:
        ref(f"materials/{material['key']}", material.get("supplier"), counterparty_keys, "поставщик")

    for part in world.parts:
        where = f"parts/{part['drawing_no']}"
        ref(where, part.get("material"), material_keys, "материал")
        ref(where, part.get("site"), site_keys, "площадка")
        for item in part.get("equipment", []):
            ref(where, item, equipment_keys, "станок")
        for item in part.get("customers", []):
            ref(where, item, counterparty_keys, "заказчик")
        for item in part.get("components", []):
            ref(where, item, part_keys, "деталь в составе узла")

    for party in world.counterparties_flat:
        where = f"counterparties/{party['key']}"
        ref(where, party.get("contract"), contract_numbers, "договор")
        ref(where, party.get("manager_role"), role_keys, "роль менеджера")
        if not FAKE_INN.match(str(party.get("inn", ""))):
            problems.append(f"{where}: ИНН «{party.get('inn')}» не из фиктивного диапазона (должен начинаться с 00)")
        email = party.get("email")
        if email and not FAKE_EMAIL.search(email):
            problems.append(f"{where}: почта «{email}» вне зоны example.com")

    for contract in world.contracts:
        ref(f"contracts/{contract['number']}", contract.get("party"), counterparty_keys, "контрагент")

    groups = {rule["group"] for rule in world.products["price_list"]["lead_time_rules"]}
    for item in world.products["items"]:
        where = f"products/{item['sku']}"
        ref(where, item.get("part"), part_keys, "деталь")
        if item.get("group") not in groups:
            problems.append(f"{where}: группа «{item.get('group')}» без срока изготовления")

    for system in world.systems:
        where = f"systems/{system['key']}"
        ref(where, system.get("owner_role"), role_keys, "владелец")
        ref(where, system.get("business_owner_role"), role_keys, "бизнес-владелец")

    for role in world.roles:
        if (owner := role.get("space_owner")) and owner not in SPACES:
            problems.append(f"roles/{role['key']}: неизвестное пространство «{owner}»")
        ref(f"roles/{role['key']}", role.get("site"), site_keys, "площадка")

    owners = [role["space_owner"] for role in world.roles if role.get("space_owner")]
    for space in sorted(SPACES - set(owners)):
        problems.append(f"roles: у пространства «{space}» нет владельца")

    for person in world.people:
        where = f"people/{person['key']}"
        ref(where, person.get("role"), role_keys, "роль")
        if not FAKE_EMAIL.search(person.get("email", "")):
            problems.append(f"{where}: почта «{person.get('email')}» вне зоны example.com")
        if not FAKE_PHONE.match(person.get("phone", "")):
            problems.append(f"{where}: телефон «{person.get('phone')}» вне фиктивного диапазона")

    for chain in world.calendar["revisions"]:
        active = [rev for rev in chain["revisions"] if rev["status"] == "active"]
        if len(active) != 1:
            problems.append(f"calendar/{chain['doc']}: действующих редакций {len(active)}, должна быть одна")

    for event in world.calendar["events"]:
        for space in event.get("spaces", []):
            if space not in SPACES:
                problems.append(f"calendar/{event['key']}: неизвестное пространство «{space}»")

    return problems


def main(root: Path | None = None) -> int:
    problems = check(World.load(root))
    for problem in problems:
        print(problem)
    print(f"нарушений: {len(problems)}")
    return 1 if problems else 0
