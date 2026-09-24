"""Специальные фикстуры корпуса: нечитаемые сканы и документы с персональными данными.

Оба класса существуют, чтобы доказать поведение, а не чтобы наполнить корпус:

* **скан** — карточка заводится, текст не извлекается, документ находится по реквизитам и в ответах не
  участвует. Это честнее, чем «распознали как смогли» (docs/spec/03, §3);
* **ПДн-фикстуры** — документы, которые система обязана остановить: не индексировать и не отправлять в
  облачную модель. Они лежат в отдельном пространстве `_pii` и в обычный поток не попадают
  (docs/spec/06, §5).

Персональные данные здесь такие же фиктивные, как и всё остальное: серия паспорта `00 00`, СНИЛС из нулей,
ИНН физического лица с префиксом `00`. Настоящих людей за ними нет, а детектор обязан сработать всё равно —
он смотрит на форму, а не на подлинность.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from rodos_corpus.generators.common import write_source, write_table_source
from rodos_corpus.world import World

PII_SPACE = "_pii"


def scans(world: World, root: Path | None = None) -> list[Path]:
    """Два PDF без текстового слоя: чертёж и архивный акт."""
    parts = world.by_key("parts")
    equipment = world.by_key("equipment")
    part = parts["45.67.89"]
    machine = equipment["shl-3m151-06"]
    written: list[Path] = []

    body = "\n".join([
        "## Чертёж детали",
        "",
        f"Обозначение: {part['drawing_no']}. Наименование: {part['name']}.",
        f"Материал: {part.get('material')}. Масса: {part.get('weight_kg')} кг.",
        "",
        "Лист 1 из 3. Формат А2, уменьшенная копия. Подписи конструктора, проверяющего и "
        "нормоконтролёра в основной надписи.",
        "",
        "Размеры, допуски формы и расположения, шероховатость и технические требования нанесены на поле "
        "чертежа и на сканированной копии читаются неуверенно.",
    ])
    card: dict[str, Any] = {
        "doc_id": "SKAN-KD-456789-L1",
        "doc_type": "drawing_scan",
        "title": f"Чертёж детали {part['drawing_no']} «{part['name']}», лист 1 (скан)",
        "org_unit": "Технологический отдел",
        "spaces": ["production"],
        "confidentiality": "internal",
        "status": "active",
        "format": "pdf_scan",
        "channel": "dropdir",
        "approved_at": date(2024, 9, 17),
        "approved_by": "Главный технолог",
        "part": part["drawing_no"],
        "text_layer": False,
        "difficulty_class": "scan_without_text",
        "expected_behaviour": "карточка создаётся, фрагментов нет, в ответах не участвует",
        "generated_by": "scans",
    }
    written.append(write_source("production", card["doc_id"], card, body, root))

    body = "\n".join([
        "## Акт ввода оборудования в эксплуатацию",
        "",
        f"Оборудование: {machine['model']}, инвентарный номер {machine['inventory_no']}.",
        "Архивная бумажная копия, отсканированная при переводе архива в электронный вид.",
        "",
        "Комиссия в составе главного механика, начальника цеха и инженера по охране труда установила, что "
        "оборудование смонтировано, испытано на холостом ходу и под нагрузкой и допускается к эксплуатации.",
        "",
        "Подписи членов комиссии и оттиск печати нанесены от руки.",
    ])
    card = {
        "doc_id": "SKAN-AKT-VVOD-1066",
        "doc_type": "commissioning_act",
        "title": f"Акт ввода в эксплуатацию станка {machine['model']}, "
                 f"инв. № {machine['inventory_no']} (скан)",
        "org_unit": "Отдел главного механика",
        "spaces": ["production"],
        "confidentiality": "internal",
        "status": "active",
        "format": "pdf_scan",
        "channel": "dropdir",
        "approved_at": date(2019, 4, 3),
        "approved_by": "Технический директор",
        "equipment": machine["inventory_no"],
        "text_layer": False,
        "difficulty_class": "scan_without_text",
        "expected_behaviour": "карточка создаётся, фрагментов нет, в ответах не участвует",
        "generated_by": "scans",
    }
    written.append(write_source("production", card["doc_id"], card, body, root))
    return written


def _pii_card(doc_id: str, doc_type: str, title: str, fmt: str, **extra: Any) -> dict[str, Any]:
    card: dict[str, Any] = {
        "doc_id": doc_id,
        "doc_type": doc_type,
        "title": title,
        "org_unit": "Отдел кадров",
        "spaces": [PII_SPACE],
        "confidentiality": "dsp",
        "status": "active",
        "format": fmt,
        "channel": "manual",
        "contains_pii": True,
        "difficulty_class": "pii_fixture",
        "expected_behaviour": "карантин: не индексировать, в облачную модель не отправлять",
        "generated_by": "pii_fixtures",
    }
    card.update(extra)
    return card


def pii_fixtures(world: World, root: Path | None = None) -> list[Path]:
    """Пять документов, на которых проверяется детектор персональных данных."""
    people = {person["key"]: person for person in world.people}
    roles = world.by_key("roles")
    written: list[Path] = []

    # 1. Приказ о приёме на работу: ФИО, дата рождения, паспорт, адрес, оклад.
    person = people["p12"]
    body = "\n".join([
        "## Приказ о приёме работника на работу",
        "",
        "1. Принять на работу с 3 августа 2026 года:",
        "",
        f"Фамилия, имя, отчество: {person['full_name']}.",
        "Дата рождения: 14 марта 1987 года.",
        "Паспорт гражданина РФ: серия 00 00, № 000001, выдан 22 апреля 2013 года.",
        "Адрес регистрации: 601900, Владимирская обл., г. Ковров, ул. Вымышленная, д. 1, кв. 1.",
        "СНИЛС: 000-000-000 00. ИНН: 000000000001.",
        "",
        f"2. Должность: {roles[person['role']]['title']}, цех №1, Ковровская площадка.",
        "3. Установить должностной оклад 96 000 рублей в месяц и надбавку за наставничество 12 %.",
        "4. Установить испытательный срок три месяца.",
        "",
        "Основание: трудовой договор и личное заявление работника.",
    ])
    card = _pii_card("PII-PRIKAZ-PRIEM-001", "hr_order",
                     "Приказ о приёме работника на работу (фикстура с ПДн)", "docx",
                     approved_at=date(2026, 8, 3), approved_by="Генеральный директор",
                     pii_kinds=["фио", "дата рождения", "паспорт", "адрес", "снилс", "инн", "оклад"])
    written.append(write_source(PII_SPACE, card["doc_id"], card, body, root))

    # 2. Личная карточка: связка ФИО + должность + персональные сведения.
    person = people["p14"]
    body = "\n".join([
        "## Личная карточка работника",
        "",
        "| Показатель | Значение |",
        "| --- | --- |",
        f"| Фамилия, имя, отчество | {person['full_name']} |",
        "| Дата рождения | 2 декабря 1991 года |",
        "| Место рождения | г. Пермь |",
        "| Гражданство | Российская Федерация |",
        "| Паспорт | серия 00 00, № 000002 |",
        "| СНИЛС | 000-000-000 01 |",
        "| ИНН | 000000000002 |",
        "| Адрес регистрации | 614014, г. Пермь, ул. Вымышленная, д. 2, кв. 2 |",
        f"| Должность | {roles[person['role']]['title']} |",
        "| Оклад | 74 000 рублей |",
        "| Состав семьи | супруг, двое детей 2015 и 2019 годов рождения |",
        "",
        "Карточка ведётся отделом кадров и хранится в кадровом деле работника.",
    ])
    card = _pii_card("PII-KARTOCHKA-T2-001", "hr_record",
                     "Личная карточка работника (фикстура с ПДн)", "docx",
                     approved_at=date(2026, 1, 15),
                     pii_kinds=["фио", "дата рождения", "паспорт", "снилс", "инн", "адрес", "оклад",
                                "состав семьи"])
    written.append(write_source(PII_SPACE, card["doc_id"], card, body, root))

    # 3. Справка о доходах: ФИО и суммы помесячно.
    person = people["p10"]
    table = {
        "name": "Доходы",
        "title": f"Справка о доходах и суммах налога физического лица за 2026 год: {person['full_name']}",
        "columns": ["Месяц", "Код дохода", "Сумма дохода, ₽", "Сумма вычета, ₽", "Налог, ₽"],
        "rows": [[f"{month:02d}.2026", 2000, 112000 + month * 1500, 1400, 14300 + month * 190]
                 for month in range(1, 9)],
    }
    card = _pii_card("PII-SPRAVKA-DOHOD-001", "income_statement",
                     "Справка о доходах физического лица (фикстура с ПДн)", "xlsx",
                     approved_at=date(2026, 9, 5), approved_by="Главный бухгалтер",
                     pii_kinds=["фио", "доходы", "налог"])
    written.append(write_table_source(PII_SPACE, card["doc_id"], card, table, root))

    # 4. Письмо с данными кандидата: самый вероятный способ, которым ПДн попадают в общий ящик.
    person = people["p18"]
    body = "\n".join([
        "Добрый день!",
        "",
        "Направляю данные кандидата на должность оператора станков с ЧПУ для оформления пропуска и "
        "подготовки трудового договора.",
        "",
        "Фамилия, имя, отчество: Тарасов Игорь Леонидович.",
        "Дата рождения: 9 июня 1994 года.",
        "Паспорт: серия 00 00, № 000003.",
        "Телефон: +7 (495) 000-00-98.",
        "Адрес проживания: 601900, Владимирская обл., г. Ковров, ул. Вымышленная, д. 3, кв. 3.",
        "Предыдущее место работы и причина увольнения указаны в приложенном резюме.",
        "",
        "Ожидаемая заработная плата — 92 000 рублей.",
        "",
        "С уважением,",
        "специалист по подбору персонала",
    ])
    card = _pii_card("PII-MAIL-KANDIDAT-001", "hr_email",
                     "Письмо с персональными данными кандидата (фикстура с ПДн)", "eml",
                     mail_from="hr@rodos-detal.example.com",
                     mail_to=person["email"],
                     mail_subject="Данные кандидата на должность оператора ЧПУ",
                     mail_date=date(2026, 7, 28),
                     pii_kinds=["фио", "дата рождения", "паспорт", "телефон", "адрес", "зарплата"])
    written.append(write_source(PII_SPACE, card["doc_id"], card, body, root))

    # 5. Табель: ФИО десяти работников в одной таблице.
    staff = [person for person in world.people
             if roles[person["role"]].get("space_owner") is None][:10]
    table = {
        "name": "Табель",
        "title": "Табель учёта рабочего времени за август 2026 года, цех №1",
        "columns": ["№", "Фамилия, имя, отчество", "Табельный номер", "Должность", "Отработано дней",
                    "Отработано часов", "Ночные часы"],
        "rows": [[index, person["full_name"], f"00{index:04d}", roles[person["role"]]["title"],
                  21, 168 - index, 16 if index % 3 == 0 else 0]
                 for index, person in enumerate(staff, start=1)],
    }
    card = _pii_card("PII-TABEL-001", "timesheet",
                     "Табель учёта рабочего времени (фикстура с ПДн)", "xlsx",
                     approved_at=date(2026, 9, 2), approved_by="Начальник цеха",
                     pii_kinds=["фио", "табельный номер", "отработанное время"])
    written.append(write_table_source(PII_SPACE, card["doc_id"], card, table, root))
    return written


GENERATORS = (scans, pii_fixtures)
