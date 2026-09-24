"""Проверки модели мира и корпуса: ссылки разрешаются, реквизиты заведомо фиктивны.

Запуск: rodos corpus lint. Линтер обязан падать до коммита, а не после публикации репозитория.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from rodos_corpus.world import World

SPACES = {"production", "finance", "sales", "it", "common"}
PII_SPACE = "_pii"
FAKE_EMAIL = re.compile(r"@[\w.-]*example\.com$")
FAKE_PHONE = re.compile(r"^\+7 \(495\) 000-00-\d\d$")

# Все числовые реквизиты корпуса начинаются с `00`, и такой префикс невозможен ни у одного
# настоящего реквизита: у ИНН и КПП первые цифры — код региона (00 не существует), ОГРН начинается
# с 1, 2, 3 или 5, у БИК первые две цифры — код страны (для России 04), у расчётного и
# корреспондентского счёта первые три — балансовый счёт (407, 301). Совпасть с живой организацией
# такие номера не могут, и это проверяется, а не декларируется.
FAKE_INN = re.compile(r"^00\d{8,10}$")
FAKE_KPP = re.compile(r"^00\d{7}$")
FAKE_OGRN = re.compile(r"^00\d{11,13}$")
FAKE_BIK = re.compile(r"^00\d{7}$")
FAKE_ACCOUNT = re.compile(r"^00\d{18}$")  # счёт — 20 знаков
REQUISITES = (
    ("inn", FAKE_INN, "ИНН"),
    ("kpp", FAKE_KPP, "КПП"),
    ("ogrn", FAKE_OGRN, "ОГРН"),
)
BANK_REQUISITES = (
    ("bik", FAKE_BIK, "БИК"),
    ("account", FAKE_ACCOUNT, "расчётный счёт"),
    ("corr_account", FAKE_ACCOUNT, "корреспондентский счёт"),
)
# Реквизит в тексте документа: слово-маркер, затем число. Проверяется так же, как в мире.
IN_TEXT = re.compile(
    r"(ИНН|КПП|ОГРНИП|ОГРН|БИК|р/с|к/с|расчётный счёт|корреспондентский счёт)[\s:№]{0,4}(\d{8,20})",
    re.IGNORECASE)


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

    for site in world.sites:
        where = f"sites/{site['key']}"
        for field, pattern, label in REQUISITES:
            value = str(site.get(field, ""))
            if not pattern.match(value):
                problems.append(f"{where}: {label} «{value}» не из фиктивного диапазона")
        for field, pattern, label in BANK_REQUISITES:
            value = str(site.get("bank", {}).get(field, ""))
            if not pattern.match(value):
                problems.append(f"{where}: {label} «{value}» не из фиктивного диапазона")

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
            problems.append(
                f"{where}: ИНН «{party.get('inn')}» не из фиктивного диапазона: нужен префикс 00")
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


def check_sources(root: Path | None = None) -> list[str]:
    """Сканирует тексты документов: реквизиты, почта и телефоны обязаны быть фиктивными.

    Мир проверяется отдельно, но в документ реквизит может попасть и мимо мира — например, если его
    напишет автор. Настоящий ИНН в публичном репозитории отменить нельзя, поэтому проверка идёт по
    тексту, а не по намерению.
    """
    from rodos_corpus.source import corpus_root

    problems: list[str] = []
    base = (root or corpus_root()) / "source"
    label = "source" if root is None else f"{base.parent.name}/source"
    for path in sorted(base.rglob("*")) if base.exists() else []:
        if not path.is_file() or path.suffix not in {".md", ".yaml"}:
            continue
        text = path.read_text(encoding="utf-8")
        where = path.relative_to(base)
        if re.search(r"^doc_type:\s*npa\s*$", text, re.M):
            continue  # настоящий НПА — его текст не наш и правкам не подлежит
        for kind, value in IN_TEXT.findall(text):
            if not value.startswith("00"):
                problems.append(f"{label}/{where}: {kind} «{value}» не из фиктивного диапазона")
        for email in set(re.findall(r"[\w.+-]+@[\w.-]+\.\w+", text)):
            if not FAKE_EMAIL.search(email):
                problems.append(f"{label}/{where}: почта «{email}» вне зоны example.com")
        for phone in set(re.findall(r"\+7\s*\(\d{3}\)\s*[\d\s-]{7,12}", text)):
            if not FAKE_PHONE.match(phone.strip()):
                problems.append(f"{label}/{where}: телефон «{phone.strip()}» вне фиктивного диапазона")
    return problems


def check_pii_isolation(docs: list[Any]) -> list[str]:
    """ПДн живут только в пространстве `_pii` и нигде больше.

    Фикстуры существуют, чтобы проверить детектор, и ровно поэтому обязаны быть изолированы: попав в
    обычный поток, они бы доказывали ровно обратное тому, ради чего сделаны (docs/spec/06, §5).
    """
    problems: list[str] = []
    for doc in docs:
        spaces = list(doc.card.get("spaces", []))
        marked = bool(doc.card.get("contains_pii"))
        if marked and spaces != [PII_SPACE]:
            problems.append(f"{doc.doc_id}: документ с ПДн в пространствах {spaces}, а не только {PII_SPACE}")
        if not marked and PII_SPACE in spaces:
            problems.append(f"{doc.doc_id}: лежит в {PII_SPACE}, но не помечен contains_pii")
        if marked and not doc.card.get("expected_behaviour"):
            problems.append(f"{doc.doc_id}: фикстура с ПДн без описания ожидаемого поведения")
    return problems


def check_links(docs: list[Any]) -> list[str]:
    """Ссылки между документами разрешаются, а цепочки редакций сходятся с обеих сторон.

    Односторонняя ссылка — самая дорогая ошибка корпуса: документ считается действующим, потому что
    никто не проставил ему `superseded_by`, и система честно отвечает по устаревшей редакции.
    """
    known = {doc.doc_id: doc for doc in docs}
    problems: list[str] = []
    for doc in docs:
        for field in ("supersedes", "superseded_by", "retracted_by"):
            target = doc.card.get(field)
            if target and target not in known:
                problems.append(f"{doc.doc_id}: поле {field} ссылается на несуществующий «{target}»")
        if (target := doc.card.get("supersedes")) and target in known:
            back = known[target].card
            if back.get("superseded_by") != doc.doc_id:
                problems.append(f"{doc.doc_id}: заменяет «{target}», но тот не ссылается обратно")
            if back.get("status") != "superseded":
                problems.append(f"{doc.doc_id}: заменяет «{target}», а у того статус «{back.get('status')}»")
    return problems


def check_names(docs: list[Any], world: World) -> list[str]:
    """Каждое ФИО в документе — из `world/people.yaml`.

    Требование не косметическое: случайно совпасть с реальным человеком в публичном репозитории легче,
    чем кажется, а вычистить потом — невозможно.
    """
    # Сравниваем по основам слов и без учёта порядка: в документах фамилия склоняется («Ушаковой»),
    # а в подписи письма имя идёт первым («Николай Сазонов»). Тащить сюда морфологический анализатор
    # ради одного правила несоразмерно, а основы из пяти букв различают вымышленных людей от наших.
    people = [{token[:5].lower() for token in person["full_name"].split()} for person in world.people]
    # Пробел, а не \s: перенос строки разделяет подпись и должность, склеивать их нельзя.
    pattern = re.compile(r"\b[А-ЯЁ][а-яё]{3,} (?:[А-ЯЁ][а-яё]{2,} [А-ЯЁ][а-яё]{2,}|[А-ЯЁ]\. ?[А-ЯЁ]\.)")
    problems: list[str] = []
    for doc in docs:
        if doc.card.get("doc_type") == "npa" or PII_SPACE in doc.card.get("spaces", []):
            continue
        text = doc.body + str(doc.table or "")
        for found in {re.sub(r"\s+", " ", match.group(0)).strip() for match in pattern.finditer(text)}:
            stems = {token[:5].lower() for token in found.split() if len(token.strip(".")) > 1}
            if not any(stems <= person for person in people):
                problems.append(f"{doc.doc_id}: ФИО «{found}» нет в world/people.yaml")
    return problems


DIFFICULTY_MINIMUMS = {
    "цепочки редакций": 6,
    "отменённые документы": 1,
    "нечитаемые сканы": 2,
    "фикстуры с ПДн": 5,
    "межпространственные документы": 20,
    "табличные документы": 20,
}


def difficulty_inventory(docs: list[Any]) -> dict[str, int]:
    """Сколько документов каждого заложенного класса сложности реально в корпусе."""
    titles: dict[str, set[str]] = {}
    for doc in docs:
        titles.setdefault(str(doc.card.get("title", "")).lower(), set()).update(doc.card.get("spaces", []))
    return {
        "цепочки редакций": sum(1 for doc in docs if doc.card.get("status") == "superseded"),
        "отменённые документы": sum(1 for doc in docs if doc.card.get("status") == "retracted"),
        "нечитаемые сканы": sum(1 for doc in docs if doc.card.get("format") == "pdf_scan"),
        "фикстуры с ПДн": sum(1 for doc in docs if doc.card.get("contains_pii")),
        "межпространственные документы": sum(1 for doc in docs if len(doc.card.get("spaces", [])) > 1),
        "табличные документы": sum(1 for doc in docs if doc.card.get("format") == "xlsx"),
        "первичка ЭДО в XML": sum(1 for doc in docs if doc.card.get("format") == "xml"),
        "письма и транскрипты": sum(1 for doc in docs if doc.card.get("format") in {"eml", "txt"}),
        "одинаковые названия в разных пространствах": sum(1 for spaces in titles.values() if len(spaces) > 1),
    }


def main(root: Path | None = None) -> int:
    from rodos_corpus.paths import stream_root
    from rodos_corpus.source import load_all

    world = World.load(root)
    docs = load_all()
    problems = (check(world) + check_sources() + check_sources(stream_root())
                + check_pii_isolation(docs) + check_links(docs) + check_names(docs, world))
    inventory = difficulty_inventory(docs)
    for name, minimum in DIFFICULTY_MINIMUMS.items():
        if inventory[name] < minimum:
            problems.append(f"классы сложности: «{name}» — {inventory[name]}, заявлено не менее {minimum}")
    for problem in problems:
        print(problem)
    print(f"нарушений: {len(problems)}")
    print("\nклассы сложности:")
    for name, count in inventory.items():
        print(f"  {name:44s} {count:4d}")
    return 1 if problems else 0
