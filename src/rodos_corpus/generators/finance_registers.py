"""Финансовые реестры и плановые документы: контрагенты, бюджеты ЦФО, план-факт, платежи.

Реестры — самый неудобный для поиска класс документов: ответ лежит в одной ячейке таблицы, а рядом
сотни похожих строк. Именно поэтому они в корпусе есть и именно поэтому их больше, чем «красиво»
(docs/spec/06, §5).
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from rodos.corpus.generators.common import write_table_source
from rodos.corpus.world import World

MONTHS = ("январь", "февраль", "март", "апрель", "май", "июнь",
          "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь")


def _rng(seed: str) -> random.Random:
    return random.Random(seed)


def counterparty_register(world: World, root: Path | None = None) -> list[Path]:
    """Реестр контрагентов с отметкой должной осмотрительности."""
    contracts = world.by_key("contracts")
    rng = _rng("counterparty_register")
    rows = []
    for party in world.counterparties_flat:
        contract = contracts.get(party.get("contract", ""), {})
        checked = date(2026, 1, 12) + timedelta(days=rng.randrange(0, 240))
        rows.append([
            party["name"],
            party["inn"],
            party["city"],
            {"supplier": "поставщик", "customer": "покупатель"}.get(
                party.get("kind", ""), "покупатель" if "buys" in party else "поставщик"),
            party.get("contract", "—"),
            f"{contract.get('signed'):%d.%m.%Y}" if contract.get("signed") else "—",
            f"{contract.get('valid_until'):%d.%m.%Y}" if contract.get("valid_until") else "—",
            str(contract.get("payment_terms", "—")),
            f"{checked:%d.%m.%Y}",
            "пройдена",
        ])
    table = {
        "name": "Контрагенты",
        "title": "Реестр контрагентов ГК «Родос-Деталь» по состоянию на 22.09.2026",
        "columns": ["Наименование", "ИНН", "Город", "Роль", "Договор", "Дата договора",
                    "Действует до", "Условия оплаты", "Дата проверки", "Должная осмотрительность"],
        "rows": rows,
    }
    card = {
        "doc_id": "REESTR-KA-2026",
        "doc_type": "counterparty_register",
        "title": "Реестр контрагентов и результаты проверки должной осмотрительности",
        "org_unit": "Финансовая служба",
        "spaces": ["finance"],
        "confidentiality": "dsp",
        "status": "active",
        "format": "xlsx",
        "channel": "manual",
        "approved_at": date(2026, 9, 22),
        "approved_by": "Финансовый директор",
        "generated_by": "counterparty_register",
    }
    return [write_table_source("finance", "REESTR-KA-2026", card, table, root)]


def cfo_budget(world: World, root: Path | None = None) -> list[Path]:
    """Бюджет доходов и расходов по центрам финансовой ответственности на 2026 год."""
    rng = _rng("cfo_budget")
    sheets = []
    for kind, label in (("expense", "Расходы"), ("income", "Доходы")):
        centres = [centre for centre in world.cfo if centre["kind"] == kind]
        rows = []
        for centre in centres:
            annual = float(centre["budget_2026_rub"])
            monthly = [round(annual / 12 * rng.uniform(0.85, 1.15), -3) for _ in MONTHS]
            scale = annual / sum(monthly)
            monthly = [round(value * scale, -3) for value in monthly]
            rows.append([centre["code"], centre["name"], centre["owner_role"], *monthly,
                         round(sum(monthly), 2)])
        sheets.append({
            "name": label,
            "title": f"Бюджет на 2026 год, {label.lower()} по ЦФО, ₽ без НДС",
            "columns": ["Код ЦФО", "Центр финансовой ответственности", "Ответственная роль",
                        *[month.capitalize() for month in MONTHS], "Итого за год"],
            "rows": rows,
        })
    card = {
        "doc_id": "BUDGET-2026",
        "doc_type": "budget",
        "title": "Бюджет доходов и расходов ГК «Родос-Деталь» на 2026 год по ЦФО",
        "org_unit": "Финансовая служба",
        "spaces": ["finance"],
        "confidentiality": "dsp",
        "status": "active",
        "format": "xlsx",
        "channel": "manual",
        "approved_at": date(2025, 12, 22),
        "approved_by": "Финансовый директор",
        "generated_by": "cfo_budget",
    }
    return [write_table_source("finance", "BUDGET-2026", card, table_of(sheets), root)]


def table_of(sheets: list[dict[str, Any]]) -> Any:
    """Один лист — словарь, несколько — список: рендерер понимает оба вида."""
    return sheets if len(sheets) > 1 else sheets[0]


def plan_fact(world: World, root: Path | None = None) -> list[Path]:
    """План-факт по ЦФО за 8 месяцев: документ, из которого спрашивают отклонения."""
    rng = _rng("plan_fact")
    rows = []
    for centre in world.cfo:
        annual = float(centre["budget_2026_rub"])
        plan = round(annual / 12 * 8, 2)
        fact = round(plan * rng.uniform(0.82, 1.18), 2)
        deviation = round(fact - plan, 2)
        rows.append([centre["code"], centre["name"],
                     "расходы" if centre["kind"] == "expense" else "доходы",
                     plan, fact, deviation, round(deviation / plan * 100, 1)])
    table = {
        "name": "План-факт",
        "title": "План-факт исполнения бюджета за январь — август 2026 г., ₽ без НДС",
        "columns": ["Код ЦФО", "Центр финансовой ответственности", "Вид", "План за 8 мес.",
                    "Факт за 8 мес.", "Отклонение, ₽", "Отклонение, %"],
        "rows": rows,
    }
    card = {
        "doc_id": "PLANFACT-2026-08",
        "doc_type": "plan_fact_report",
        "title": "Отчёт о исполнении бюджета за январь — август 2026 года",
        "org_unit": "Финансовая служба",
        "spaces": ["finance"],
        "confidentiality": "dsp",
        "status": "active",
        "format": "xlsx",
        "channel": "manual",
        "approved_at": date(2026, 9, 10),
        "approved_by": "Финансовый директор",
        "generated_by": "plan_fact",
    }
    return [write_table_source("finance", "PLANFACT-2026-08", card, table, root)]


def payment_registers(world: World, root: Path | None = None) -> list[Path]:
    """Реестры платежей на день: здесь видно, кто и до какой суммы согласует (docs/spec/02)."""
    parties = world.counterparties_flat
    limits = {role["title"]: role.get("payment_limit_rub")
              for role in world.roles if role.get("payment_limit_rub")}
    written: list[Path] = []
    for index, day in enumerate((date(2026, 9, 8), date(2026, 9, 15), date(2026, 9, 22))):
        doc_id = f"REESTR-PLAT-{day:%Y%m%d}"
        rng = _rng(doc_id)
        rows = []
        for party in rng.sample(parties, k=9):
            amount = float(rng.randrange(35, 4200) * 1000)
            approver = next((title for title, limit in sorted(limits.items(), key=lambda x: x[1])
                             if amount <= limit), "Генеральный директор")
            rows.append([party.get("contract", "—"), party["name"], party["inn"], amount,
                         approver, "оплачено" if rng.random() > 0.25 else "к оплате"])
        table = {
            "name": "Реестр",
            "title": f"Реестр платежей на {day:%d.%m.%Y}",
            "columns": ["Договор", "Получатель", "ИНН", "Сумма, ₽", "Согласует", "Статус"],
            "rows": [*rows, ["", "Итого", "", sum(row[3] for row in rows), "", ""]],
        }
        card = {
            "doc_id": doc_id,
            "doc_type": "payment_register",
            "title": f"Реестр платежей на {day:%d.%m.%Y}",
            "org_unit": "Финансовая служба",
            "spaces": ["finance"],
            "confidentiality": "dsp",
            "status": "active",
            "format": "xlsx",
            "channel": "manual",
            "approved_at": day,
            "approved_by": "Казначей",
            "generated_by": "payment_registers",
        }
        written.append(write_table_source("finance", doc_id, card, table, root))
        index += 1
    return written


def document_flow_schedule(world: World, root: Path | None = None) -> list[Path]:
    """График документооборота: кто, что, когда и кому передаёт."""
    rows = [
        ["УПД на реализацию", "Отдел продаж", "Бухгалтерия", "в день отгрузки", "ЭДО",
         "Бухгалтер по расчётам с контрагентами"],
        ["УПД от поставщика", "Отдел снабжения", "Бухгалтерия", "1 рабочий день с даты получения",
         "ЭДО", "Бухгалтер по расчётам с контрагентами"],
        ["Счёт на оплату", "Инициатор платежа", "Казначей", "не позднее 3 рабочих дней до срока оплаты",
         "ЭДО", "Казначей"],
        ["Акт выполненных работ", "Инициатор договора", "Бухгалтерия", "3 рабочих дня с даты подписания",
         "ЭДО", "Главный бухгалтер"],
        ["Акт сверки", "Бухгалтерия", "Контрагент", "до 20-го числа месяца, следующего за полугодием",
         "ЭДО", "Бухгалтер по расчётам с контрагентами"],
        ["Авансовый отчёт", "Подотчётное лицо", "Бухгалтерия", "3 рабочих дня с даты возвращения",
         "бумага", "Главный бухгалтер"],
        ["Лимитно-заборная карта", "Склад материалов", "Бухгалтерия", "до 5-го числа следующего месяца",
         "1С:ERP", "Бухгалтер по учёту материалов"],
        ["Акт о браке", "ОТК", "Бухгалтерия", "1 рабочий день с даты оформления", "1С:ERP",
         "Главный бухгалтер"],
        ["Табель учёта рабочего времени", "Начальник цеха", "Отдел кадров", "до 3-го числа следующего месяца",
         "1С:ERP", "Специалист по кадрам"],
        ["Заявка на закупку", "Инициатор", "Отдел снабжения", "не позднее 10 рабочих дней до потребности",
         "1С:ERP", "Начальник отдела снабжения"],
        ["Договор на подпись", "Инициатор договора", "Юридический отдел", "5 рабочих дней на согласование",
         "ЭДО", "Юрисконсульт"],
        ["Налоговое требование", "Бухгалтерия", "Ответственный исполнитель",
         "ответ в срок, указанный в требовании", "ЭДО", "Главный бухгалтер"],
    ]
    table = {
        "name": "График",
        "title": "График документооборота ГК «Родос-Деталь», приложение к учётной политике",
        "columns": ["Документ", "Кто оформляет", "Кому передаёт", "Срок передачи", "Канал",
                    "Кто контролирует"],
        "rows": rows,
    }
    card = {
        "doc_id": "GRAFIK-DO-2026",
        "doc_type": "document_flow_schedule",
        "title": "График документооборота на 2026 год",
        "org_unit": "Бухгалтерия",
        "spaces": ["finance", "common"],
        "confidentiality": "internal",
        "status": "active",
        "format": "xlsx",
        "channel": "manual",
        "approved_at": date(2025, 12, 29),
        "approved_by": "Главный бухгалтер",
        "generated_by": "document_flow_schedule",
    }
    return [write_table_source("finance", "GRAFIK-DO-2026", card, table, root)]


def writeoff_norms(world: World, root: Path | None = None) -> list[Path]:
    """Нормативы списания материалов: тот же факт, что в нормах расхода, но в деньгах.

    Межпространственная ловушка: одна и та же норма живёт в производственном и финансовом документе,
    и ответ обязан ссылаться на тот, о котором спрашивают.
    """
    rows = []
    for material in world.materials_flat:
        if material.get("norm_per_part") is None and material.get("norm_per_month") is None:
            continue
        norm = material.get("norm_per_part") or material.get("norm_per_month")
        rows.append([
            material.get("grade") or material.get("name"),
            material.get("unit", "кг"),
            norm,
            "на деталь" if material.get("norm_per_part") else "на месяц",
            material.get("price_rub", "—"),
            "счёт 20 «Основное производство»" if material.get("norm_per_part")
            else "счёт 25 «Общепроизводственные расходы»",
        ])
    table = {
        "name": "Нормативы",
        "title": "Нормативы списания материалов и инструмента на 2026 год",
        "columns": ["Наименование", "Ед. изм.", "Норма", "База нормирования", "Цена, ₽",
                    "Счёт списания"],
        "rows": rows,
    }
    card = {
        "doc_id": "NORM-SPIS-2026",
        "doc_type": "writeoff_norms",
        "title": "Нормативы списания материалов и инструмента на 2026 год",
        "org_unit": "Бухгалтерия",
        "spaces": ["finance", "production"],
        "confidentiality": "internal",
        "status": "active",
        "format": "xlsx",
        "channel": "manual",
        "approved_at": date(2026, 1, 19),
        "approved_by": "Главный бухгалтер",
        "generated_by": "writeoff_norms",
    }
    return [write_table_source("finance", "NORM-SPIS-2026", card, table, root)]


GENERATORS = (counterparty_register, cfo_budget, plan_fact, payment_registers,
              document_flow_schedule, writeoff_norms)
