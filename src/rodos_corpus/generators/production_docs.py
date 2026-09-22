"""Производственные документы из модели мира: паспорта станков, ППР, нормы, сменные задания,
протоколы испытаний, акты о браке и лимитно-заборные карты.

Всё, что здесь порождается, имеет проверяемые числа: они же становятся эталонными ответами оценки.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

from rodos.corpus.generators.common import write_source, write_table_source
from rodos.corpus.world import World

SEED = 20260922


def equipment_passports(world: World, root: Path | None = None) -> list[Path]:
    """Паспорт и руководство по эксплуатации на станок — PDF, как их присылает поставщик."""
    workshops = world.by_key("workshops")
    written: list[Path] = []
    for machine in world.equipment:
        doc_id = machine["passport_doc"]
        shop = workshops[machine["workshop"]]
        commissioned: date = machine["commissioned"]
        interval = int(machine["maintenance_interval_days"])
        danger_note = ("5.3. Оборудование относится к опасному производственному объекту; "
                       "обслуживание выполняется по наряду-допуску."
                       if machine["key"].startswith("galv-") else "")
        body = f"""## 1. Общие сведения

| Параметр | Значение |
| --- | --- |
| Наименование | {machine['name']} |
| Модель | {machine['model']} |
| Инвентарный номер | {machine['inventory_no']} |
| Место установки | {shop['name']}, {shop['areas'][0]} |
| Дата ввода в эксплуатацию | {commissioned:%d.%m.%Y} |
| Периодичность технического обслуживания | {interval} суток |

## 2. Условия эксплуатации

2.1. Температура окружающего воздуха от +10 до +35 °С, относительная влажность не более 80 %.

2.2. Питание от сети 380 В, 50 Гц. Отклонение напряжения не более ±10 %.

2.3. Станок должен быть заземлён. Работа при неисправном заземлении запрещена.

## 3. Техническое обслуживание

3.1. Ежесменное обслуживание выполняет оператор: очистка от стружки, проверка уровня СОЖ и масла,
осмотр ограждений.

3.2. Плановое техническое обслуживание выполняет служба главного механика с периодичностью
{interval} суток по графику ППР.

3.3. Перечень работ планового обслуживания:

- проверка и подтяжка крепёжных соединений;
- замена масла в редукторах приводов при наработке свыше 2 000 часов;
- проверка точности позиционирования по контрольному образцу;
- проверка срабатывания блокировок и аварийного останова.

3.4. Результаты обслуживания заносятся в журнал технического обслуживания станка.

## 4. Порядок вывода в ремонт

4.1. Вывод станка в плановый ремонт согласует главный механик, внеплановый — по заявке начальника цеха.

4.2. При отказе оборудования оператор немедленно прекращает работу, отключает станок и сообщает мастеру
участка. Мастер оформляет заявку на ремонт в тот же день.

## 5. Требования безопасности

5.1. К работе допускаются лица, прошедшие обучение и инструктаж по охране труда.

5.2. Запрещается работа со снятыми или неисправными ограждениями, а также очистка станка при включённом
приводе.

{danger_note}
"""
        card = {
            "doc_id": doc_id,
            "doc_type": "equipment_passport",
            "title": f"Паспорт и руководство по эксплуатации: {machine['name']} {machine['model']}",
            "org_unit": "Служба главного механика",
            "spaces": ["production"],
            "confidentiality": "internal",
            "status": "active",
            "format": "pdf",
            "channel": "dropdir",
            "approved_at": commissioned,
            "effective_from": commissioned,
            "plants": [shop["site"]],
            "equipment": machine["key"],
            "generated_by": "equipment_passports",
        }
        written.append(write_source("production", doc_id, card, body, root))
    return written


def ppr_schedule(world: World, root: Path | None = None) -> list[Path]:
    """График планово-предупредительного ремонта на год — XLSX по всем станкам."""
    workshops = world.by_key("workshops")
    rows = []
    for machine in world.equipment:
        shop = workshops[machine["workshop"]]
        interval = int(machine["maintenance_interval_days"])
        start = date(2026, 1, 15) + timedelta(days=(hash(machine["key"]) % 30))
        dates = []
        current = start
        while current.year == 2026:
            dates.append(f"{current:%d.%m}")
            current += timedelta(days=interval)
        rows.append([
            machine["inventory_no"], machine["model"], shop["name"], interval,
            ", ".join(dates[:6]) + ("…" if len(dates) > 6 else ""),
            "служба главного механика",
        ])
    card = {
        "doc_id": "PPR-2026",
        "doc_type": "maintenance_plan",
        "title": "График планово-предупредительного ремонта оборудования на 2026 год",
        "org_unit": "Служба главного механика",
        "spaces": ["production"],
        "confidentiality": "internal",
        "status": "active",
        "format": "xlsx",
        "channel": "dropdir",
        "approved_at": date(2025, 12, 20),
        "effective_from": date(2026, 1, 1),
        "effective_to": date(2026, 12, 31),
        "approved_by": "Главный механик",
        "generated_by": "ppr_schedule",
    }
    table = {
        "name": "ППР 2026",
        "title": "График ППР на 2026 год, ГК «Родос-Деталь»",
        "columns": ["Инв. №", "Модель", "Цех", "Периодичность, сут.", "Плановые даты", "Исполнитель"],
        "rows": rows,
    }
    return [write_table_source("production", card["doc_id"], card, table, root)]


def consumption_norms(world: World, root: Path | None = None) -> list[Path]:
    """Нормы расхода материалов, инструмента и СОЖ — XLSX, два листа."""
    tooling_rows = [[item["name"], item["unit"], item["norm_per_part"], "на одну деталь",
                     world.by_key("counterparties")[item["supplier"]]["name"]]
                    for item in world.materials["tooling"]]
    consumable_rows = [[item["name"], item["unit"], item["norm_per_part"], item.get("note", "на одну деталь"),
                        world.by_key("counterparties")[item["supplier"]]["name"]]
                       for item in world.materials["consumables"]]
    card = {
        "doc_id": "NORM-RASH-2026",
        "doc_type": "consumption_norm",
        "title": "Нормы расхода инструмента и расходных материалов на 2026 год",
        "org_unit": "Технологический отдел",
        "spaces": ["production"],
        "confidentiality": "internal",
        "status": "active",
        "format": "xlsx",
        "channel": "dropdir",
        "approved_at": date(2026, 1, 12),
        "effective_from": date(2026, 2, 1),
        "approved_by": "Главный технолог",
        "generated_by": "consumption_norms",
    }
    table = [
        {"name": "Инструмент", "title": "Нормы расхода режущего инструмента",
         "columns": ["Наименование", "Ед. изм.", "Норма", "Основание", "Поставщик"], "rows": tooling_rows},
        {"name": "Расходные материалы", "title": "Нормы расхода СОЖ, химикатов и масел",
         "columns": ["Наименование", "Ед. изм.", "Норма", "Примечание", "Поставщик"],
         "rows": consumable_rows},
    ]
    return [write_table_source("production", card["doc_id"], card, table, root)]


def shift_tasks(world: World, root: Path | None = None, count: int = 6) -> list[Path]:
    """Сменные задания по цехам — XLSX, самые «живые» документы цеха."""
    random.seed(SEED)
    parts = [part for part in world.parts if part.get("route")]
    workshops = [shop for shop in world.workshops if shop["equipment"]]
    written: list[Path] = []
    for index in range(count):
        shop = workshops[index % len(workshops)]
        day = date(2026, 9, 1) + timedelta(days=index * 2)
        rows = []
        for part in random.sample(parts, 5):
            plan = random.choice([20, 30, 40, 50, 60, 80, 100])
            done = plan - random.choice([0, 0, 0, 2, 5, 8])
            rows.append([part["drawing_no"], part["name"][:45], random.choice(part["route"]).split()[0],
                         plan, done, plan - done, "мастер участка"])
        doc_id = f"SMZ-{day:%Y%m%d}-{shop['key'].upper()}"
        card = {
            "doc_id": doc_id,
            "doc_type": "shift_task",
            "title": f"Сменное задание, {shop['name']}, {day:%d.%m.%Y}",
            "org_unit": shop["name"],
            "spaces": ["production"],
            "confidentiality": "internal",
            "status": "active",
            "format": "xlsx",
            "channel": "dropdir",
            "approved_at": day,
            "effective_from": day,
            "effective_to": day,
            "approved_by": "Начальник цеха",
            "plants": [shop["site"]],
            "generated_by": "shift_tasks",
        }
        table = {
            "name": f"{day:%d.%m}",
            "title": f"Сменное задание на {day:%d.%m.%Y}, {shop['name']}",
            "columns": ["Обозначение", "Наименование", "Операция", "План, шт.", "Сдано, шт.",
                        "Отклонение", "Ответственный"],
            "rows": rows,
        }
        written.append(write_table_source("production", doc_id, card, table, root))
    return written


def test_protocols(world: World, root: Path | None = None) -> list[Path]:
    """Протоколы испытаний и измерений — PDF, с конкретными замерами."""
    random.seed(SEED + 1)
    written: list[Path] = []
    candidates = [part for part in world.parts if part.get("tolerances")]
    for index, part in enumerate(random.sample(candidates, 6)):
        day = date(2026, 6, 4) + timedelta(days=index * 9)
        doc_id = f"PROT-{day:%Y%m%d}-{index + 1:02d}"
        rows = []
        for key, value in list(part["tolerances"].items())[:4]:
            measured = value
            if isinstance(value, (int, float)):
                measured = round(float(value) * random.uniform(0.6, 0.95), 3)
            rows.append(f"| {key} | {value} | {measured} | соответствует |")
        body = f"""## 1. Объект испытаний

1.1. Деталь {part['drawing_no']} «{part['name']}», партия № {random.randint(120, 480)}, количество
{random.choice([20, 30, 50])} шт.

1.2. Основание: технологическая карта ТК-{str(part['drawing_no']).replace('.', '')}-r1, регламент
ОТК-РЕГЛ-003 ред. 3.

## 2. Условия и средства измерений

2.1. Температура в помещении 20 ± 2 °С, влажность 55 %.

2.2. Применённые средства измерений: микрометр МК 0-25 (поверка до {day.year}-12-31), индикаторная
головка ИЧ-10, твердомер ТР 5006.

## 3. Результаты

| Параметр | Норма | Фактически | Заключение |
| --- | --- | --- | --- |
{chr(10).join(rows)}

## 4. Заключение

4.1. Партия соответствует требованиям технологической карты и допущена к передаче на следующую операцию.

4.2. Протокол хранится в ОТК в течение трёх лет.
"""
        card = {
            "doc_id": doc_id,
            "doc_type": "test_report",
            "title": f"Протокол измерений партии детали {part['drawing_no']} от {day:%d.%m.%Y}",
            "org_unit": "Отдел технического контроля",
            "spaces": ["production"],
            "confidentiality": "internal",
            "status": "active",
            "format": "pdf",
            "channel": "dropdir",
            "approved_at": day,
            "approved_by": "Начальник ОТК",
            "part": part["drawing_no"],
            "generated_by": "test_protocols",
        }
        written.append(write_source("production", doc_id, card, body, root))
    return written


def defect_acts(world: World, root: Path | None = None) -> list[Path]:
    """Акты о браке — документ, из которого начинается разбор и претензия поставщику."""
    random.seed(SEED + 2)
    # Деталь и причина закреплены за каждым актом, а не выбираются случайно: на эти акты ссылаются
    # отчёты 8D, претензии и разборы инцидентов, и расхождение между актом и тем, что о нём написано
    # в другом документе, обесценивает весь корпус — его смысл именно в связности.
    acts = [
        (date(2026, 5, 12), 1, "45.67.90", 42,
         "занижение твёрдости после закалки ТВЧ", "загрязнение индуктора установки ОС-1155",
         "партия направлена на повторную термообработку", "разбор оформлен отчётом 8D-2026-03"),
        (date(2026, 6, 2), 2, "61.05.20", 88,
         "раковины на литой поверхности заготовки", "дефект отливки поставщика по договору ЛД-2024/27",
         "заготовки возвращены поставщику", "оформлена претензия ПРЕТ-2026-01"),
        (date(2026, 6, 23), 3, "45.67.89", 120,
         "превышение радиального биения сверх нормы чертежа", "износ центров станка 3М151, инв. № ОС-1066",
         "детали направлены на перешлифовку, партия заказчику не отгружена",
         "по рекламации АО «Редмаш» оформлен отчёт 8D-2026-01 и извещение ИЗВ-2026-004"),
        (date(2026, 7, 14), 4, "88.14.42", 64,
         "несоответствие толщины цинкового покрытия",
         "нестабильность выпрямителя линии АГ-40, инв. № ОС-0903",
         "детали направлены на повторное покрытие",
         "разбор оформлен отчётом 8D-2026-02, отказ выпрямителя разобран в ИНЦ-2026-05"),
    ]
    parts = world.by_key("parts")
    written: list[Path] = []
    for day, number, drawing, batch, defect, cause, decision, link in acts:
        part = parts[drawing]
        quantity = random.randint(3, 18)
        operation = part["route"][-1] if part.get("route") else "070 контроль ОТК"
        doc_id = f"AKT-BRAK-{day:%Y%m%d}-{number:02d}"
        body = f"""## 1. Обстоятельства

1.1. При контроле партии детали {part['drawing_no']} «{part['name']}» выявлено {defect}.

1.2. Количество забракованных деталей: {quantity} шт. из партии {batch} шт.

1.3. Операция, на которой выявлено несоответствие: {operation}.

## 2. Причина

2.1. Установленная причина: {cause}.

2.2. Ответственное подразделение определяется по результатам разбора у главного технолога.

## 3. Решение

3.1. Принятое решение: {decision}.

3.2. Стоимость брака относится на затраты цеха и учитывается в отчёте за месяц.

3.3. Корректирующие действия и срок их выполнения определяются отдельным протоколом разбора: {link}.

## 4. Подписи

Контролёр ОТК, мастер участка, начальник цеха.
"""
        card = {
            "doc_id": doc_id,
            "doc_type": "defect_act",
            "title": f"Акт о браке по детали {part['drawing_no']} от {day:%d.%m.%Y}",
            "org_unit": "Отдел технического контроля",
            "spaces": ["production"],
            "confidentiality": "internal",
            "status": "active",
            "format": "docx",
            "channel": "dropdir",
            "approved_at": day,
            "approved_by": "Начальник ОТК",
            "part": part["drawing_no"],
            "generated_by": "defect_acts",
        }
        written.append(write_source("production", doc_id, card, body, root))
    return written


def limit_cards(world: World, root: Path | None = None) -> list[Path]:
    """Лимитно-заборные карты — выдача материалов в цех, XLSX."""
    random.seed(SEED + 3)
    rows = []
    for material in world.materials["steels"] + world.materials["consumables"]:
        limit = random.choice([200, 350, 500, 800, 1200])
        issued = int(limit * random.uniform(0.55, 0.95))
        rows.append([material.get("grade", material.get("name")),
                     material.get("form", material.get("unit", "—")),
                     limit, issued, limit - issued, "цех №1"])
    card = {
        "doc_id": "LZK-2026-09",
        "doc_type": "limit_card",
        "title": "Лимитно-заборная карта на сентябрь 2026 года, цех №1",
        "org_unit": "Цех №1, токарно-фрезерный",
        "spaces": ["production"],
        "confidentiality": "internal",
        "status": "active",
        "format": "xlsx",
        "channel": "dropdir",
        "approved_at": date(2026, 8, 28),
        "effective_from": date(2026, 9, 1),
        "effective_to": date(2026, 9, 30),
        "approved_by": "Начальник цеха",
        "plants": ["kovrov"],
        "generated_by": "limit_cards",
    }
    table = {
        "name": "Сентябрь 2026",
        "title": "Лимитно-заборная карта, цех №1, сентябрь 2026",
        "columns": ["Материал", "Вид", "Лимит", "Выдано", "Остаток лимита", "Подразделение"],
        "rows": rows,
    }
    return [write_table_source("production", card["doc_id"], card, table, root)]


GENERATORS = (equipment_passports, ppr_schedule, consumption_norms, shift_tasks, test_protocols,
              defect_acts, limit_cards)
