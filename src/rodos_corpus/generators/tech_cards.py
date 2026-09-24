"""Технологические карты и операционные карты из world/parts.yaml.

Техкарта — единица вопроса в цехе («что делать на операции 025?»), поэтому операция становится отдельным
пунктом с собственной нумерацией: на неё ссылается ответ ассистента.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

from rodos_corpus.generators.common import write_source
from rodos_corpus.world import World

# Режимы резания по видам операций: подставляются в карту, чтобы в корпусе были проверяемые числа.
MODES: dict[str, dict[str, Any]] = {
    "токарная": {"tool": "Резец проходной с пластиной CNMG 120408", "v": "180…220 м/мин",
                 "s": "0,25 мм/об", "t": "1,5…2,5 мм", "cool": "СОЖ ЭТ-2, 5…7 %"},
    "фрезерная": {"tool": "Фреза торцевая ø63, 5 зубьев", "v": "160…190 м/мин",
                  "s": "0,15 мм/зуб", "t": "до 3 мм", "cool": "СОЖ ЭТ-2, 5…7 %"},
    "зубофрезерная": {"tool": "Червячная фреза m по чертежу, класс АА", "v": "45…60 м/мин",
                      "s": "2,0 мм/об", "t": "по целому", "cool": "СОЖ ЭТ-2, 7 %"},
    "зубострогальная": {"tool": "Строгальный резец конический", "v": "30…40 м/мин",
                        "s": "1,2 мм/дв. ход", "t": "по целому", "cool": "СОЖ ЭТ-2, 7 %"},
    "шевингование": {"tool": "Шевер дисковый", "v": "120 м/мин", "s": "0,2 мм/об", "t": "0,05…0,08 мм",
                     "cool": "масло индустриальное"},
    "круглошлифовальная": {"tool": "Круг 600×63×305 25А", "v": "35 м/с", "s": "0,004 мм/ход",
                           "t": "0,15…0,25 мм на сторону", "cool": "СОЖ ЭТ-2, 3 %"},
    "плоскошлифовальная": {"tool": "Круг 400×40×127 25А", "v": "30 м/с", "s": "0,01 мм/ход",
                           "t": "0,1 мм", "cool": "СОЖ ЭТ-2, 3 %"},
    "сверлильная": {"tool": "Сверло ø12 Р6М5", "v": "25…30 м/мин", "s": "0,12 мм/об", "t": "—",
                    "cool": "СОЖ ЭТ-2, 5 %"},
    "расточная": {"tool": "Расточная головка с пластиной CCMT", "v": "150 м/мин", "s": "0,12 мм/об",
                  "t": "0,5…1,0 мм", "cool": "СОЖ ЭТ-2, 5 %"},
    "хонингование": {"tool": "Хон с брусками 63С", "v": "40 м/мин", "s": "—", "t": "0,03…0,05 мм",
                     "cool": "масло хонинговальное"},
    "термообработка": {"tool": "—", "v": "—", "s": "—", "t": "—", "cool": "—"},
    "подготовительная": {"tool": "—", "v": "—", "s": "—", "t": "—", "cool": "—"},
    "разметка": {"tool": "Разметочный инструмент, плита поверочная", "v": "—", "s": "—",
                 "t": "—", "cool": "—"},
    "штамповка": {"tool": "Штамп вырубной", "v": "—", "s": "—", "t": "—", "cool": "—"},
    "хромирование": {"tool": "—", "v": "—", "s": "—", "t": "—", "cool": "электролит хромовый"},
    "цинкование": {"tool": "—", "v": "—", "s": "—", "t": "—", "cool": "электролит цинкатный"},
    "полирование": {"tool": "Круг войлочный, паста ГОИ", "v": "20 м/с", "s": "—", "t": "—", "cool": "—"},
    "контроль": {"tool": "Штангенциркуль, микрометр, индикаторная головка", "v": "—", "s": "—",
                 "t": "—", "cool": "—"},
    "сборка": {"tool": "Оснастка сборочная, пресс", "v": "—", "s": "—", "t": "—", "cool": "—"},
    "обкатка": {"tool": "Стенд обкатки", "v": "—", "s": "—", "t": "—", "cool": "масло И-20А"},
    "испытание": {"tool": "Стенд испытаний", "v": "—", "s": "—", "t": "—", "cool": "—"},
    "консервация": {"tool": "—", "v": "—", "s": "—", "t": "—", "cool": "масло К-17"},
}
DEFAULT_MODE = {"tool": "по технологической оснастке", "v": "—", "s": "—", "t": "—", "cool": "СОЖ ЭТ-2, 5 %"}


def _mode(operation: str) -> dict[str, Any]:
    for key, value in MODES.items():
        if key in operation:
            return value
    return DEFAULT_MODE


# Какой станок выполняет операцию: по виду операции выбирается подходящее оборудование детали.
MACHINE_PREFIXES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("хонингование", ("cnc-", "tok-")),
    ("расточная", ("cnc-", "frz-")),
    ("токарная", ("tok-", "cnc-")),
    ("зубофрезерная", ("frz-", "cnc-")),
    ("зубострогальная", ("frz-", "cnc-")),
    ("шевингование", ("frz-",)),
    ("фрезерная", ("frz-", "cnc-")),
    ("сверлильная", ("frz-", "cnc-")),
    ("шлифовальная", ("shl-",)),
    ("твч", ("term-tvch",)),
    ("печная", ("term-sshz",)),
    ("термообработка", ("term-",)),
    ("хромирование", ("galv-ag25",)),
    ("цинкование", ("galv-ag40",)),
    ("штамповка", ("press-",)),
    ("сборка", ("press-",)),
    ("испытание", ("stend-",)),
    ("обкатка", ("stend-", "press-")),
)


def _machine_for(operation: str, machines: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Станок из числа закреплённых за деталью, подходящий под вид операции."""
    for keyword, prefixes in MACHINE_PREFIXES:
        if keyword in operation:
            for prefix in prefixes:
                for machine in machines:
                    if machine["key"].startswith(prefix):
                        return machine
            return None
    return None


def _tolerance_lines(part: dict[str, Any]) -> list[str]:
    labels = {
        "runout_mm": "радиальное биение, мм, не более",
        "surface_ra": "шероховатость Ra, мкм, не более",
        "hardness_hrc": "твёрдость, HRC",
        "diameter_field": "поле допуска диаметра",
        "bore_field": "поле допуска отверстия",
        "gear_grade": "степень точности зубчатого венца",
        "flatness_mm": "отклонение от плоскостности, мм",
        "axis_distance_mm": "межосевое расстояние",
        "coating": "покрытие",
        "coating_um": "толщина покрытия, мкм",
        "thread": "резьба",
        "balance_grade": "класс балансировки",
        "straightness_mm_per_m": "прямолинейность, мм/м",
        "width_field": "поле допуска ширины",
        "thickness_mm": "толщина, мм",
        "test_pressure_bar": "давление испытания, бар",
        "noise_db": "уровень шума, дБ",
        "run_in_min": "время обкатки, мин",
        "stroke_mm": "ход, мм",
        "oil_leak": "течь масла",
        "leak": "утечки",
        "travel_mm": "ход натяжения, мм",
    }
    return [f"| {labels.get(key, key)} | {value} |" for key, value in (part.get("tolerances") or {}).items()]


def generate(world: World, root: Path | None = None, limit: int | None = None) -> list[Path]:
    """Пишет исходники техкарт. Возвращает список созданных файлов."""
    materials = world.by_key("materials")
    equipment = world.by_key("equipment")
    workshops = {machine["key"]: machine["workshop"] for machine in world.equipment}
    written: list[Path] = []
    base_date = date(2026, 3, 2)

    for index, part in enumerate(world.parts[:limit]):
        drawing = str(part["drawing_no"])
        doc_id = f"TK-{drawing.replace('.', '')}-r1"
        approved = base_date + timedelta(days=index * 3)
        material = materials.get(part.get("material") or "", {})
        machines = [equipment[key] for key in part.get("equipment", []) if key in equipment]
        shops = sorted({workshops[key] for key in part.get("equipment", []) if key in workshops})

        body: list[str] = []
        body.append("## 1. Общие сведения\n")
        body.append("| Параметр | Значение |")
        body.append("| --- | --- |")
        body.append(f"| Обозначение детали | {drawing} |")
        body.append(f"| Наименование | {part['name']} |")
        body.append(f"| Материал | {material.get('grade', 'по сборочному чертежу')} |")
        body.append(f"| Заготовка | {part.get('blank', '—')} |")
        body.append(f"| Масса, кг | {part.get('weight_kg', '—')} |")
        body.append(f"| Площадка | {part['site']} |")
        body.append(f"| Цеха | {', '.join(shops) if shops else 'сборочный участок'} |\n")

        if components := part.get("components"):
            body.append("1.1. Сборочная единица комплектуется деталями: " + ", ".join(components) + ".\n")

        body.append("## 2. Маршрут обработки\n")
        for operation in part.get("route", []):
            number, _, name = str(operation).partition(" ")
            mode = _mode(name)
            machine = _machine_for(name, machines)
            body.append(f"### {number} {name[:1].upper() + name[1:]}\n")
            where = (f"{machine['model']}, инв. № {machine['inventory_no']}" if machine
                     else "по указанию мастера участка")
            body.append(f"Оборудование: {where}.")
            body.append(f"Инструмент: {mode['tool']}.")
            if mode["v"] != "—":
                body.append(f"Режимы: скорость {mode['v']}, подача {mode['s']}, глубина {mode['t']}.")
            if mode["cool"] != "—":
                body.append(f"Охлаждение: {mode['cool']}.")
            body.append("")

        body.append("## 3. Контролируемые параметры\n")
        body.append("| Параметр | Норма |")
        body.append("| --- | --- |")
        body.extend(_tolerance_lines(part))
        body.append("")
        body.append("3.1. Контроль выполняется на операции 070 контролёром ОТК по методике ОТК-МИ-001.")
        body.append("3.2. При отклонении параметра деталь не передаётся на следующую операцию; оформляется "
                    "извещение о несоответствии по регламенту ОТК-РЕГЛ-003.\n")
        body.append("## 4. Требования охраны труда\n")
        body.append("4.1. К работе допускаются лица, прошедшие инструктаж по инструкции ИОТ-005 «Общие "
                    "требования охраны труда для работников механических цехов».")
        body.append("4.2. Применение средств индивидуальной защиты обязательно на всех операциях "
                    "механической обработки.")

        card = {
            "doc_id": doc_id,
            "doc_type": "tech_card",
            "title": f"Технологическая карта на деталь {drawing} «{part['name']}»",
            "org_unit": "Технологический отдел",
            "spaces": ["production"],
            "confidentiality": "internal",
            "status": "active",
            "format": "docx",
            "channel": "dropdir",
            "version": "ред. 1",
            "approved_at": approved,
            "effective_from": approved + timedelta(days=7),
            "approved_by": "Главный технолог",
            "plants": [part["site"]],
            "part": drawing,
            "generated_by": "tech_cards",
        }
        written.append(write_source("production", doc_id, card, "\n".join(body), root))
    return written
