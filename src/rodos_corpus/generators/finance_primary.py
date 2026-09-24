"""Первичные документы финансов: УПД, счета, акты выполненных работ, акты сверки.

Первичка порождается из договоров, а не выдумывается: у документа обязаны сходиться стороны, номер
договора, сроки оплаты и суммы — иначе вопрос «когда платить по этой поставке» не имеет проверяемого
ответа, а он один из самых частых в финансовом пространстве (docs/spec/02).

УПД рендерится в XML: у ЭДО-первички карточка почти целиком структурна, и приём обязан уметь читать
дерево, а не пересказ (docs/spec/06, §6).
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from rodos_corpus.generators.common import write_source, write_table_source
from rodos_corpus.world import World

VAT_RATE = 20
UPD_START = date(2026, 1, 16)


def _rng(seed: str) -> random.Random:
    """Детерминированный генератор: перегенерация обязана давать тот же корпус."""
    return random.Random(seed)


def _money(value: float) -> str:
    return f"{value:.2f}"


def _org(site: dict[str, Any]) -> dict[str, str]:
    return {
        "name": str(site["legal_name"]),
        "inn": str(site["inn"]),
        "kpp": str(site["kpp"]),
        "address": str(site["address"]),
    }


def _party(counterparty: dict[str, Any]) -> dict[str, str]:
    """Контрагент как сторона документа. КПП выводится из ИНН по тому же фиктивному правилу."""
    inn = str(counterparty["inn"])
    return {
        "name": str(counterparty["name"]),
        "inn": inn,
        "kpp": f"00{inn[2:6]}001",
        "address": f"{counterparty['city']}",
    }


def _upd_xml(number: str, issued: date, seller: dict[str, str], buyer: dict[str, str],
             contract: dict[str, Any], lines: list[dict[str, Any]], signer: str) -> str:
    """Упрощённое дерево УПД по логике формата ФНС: стороны, основание, таблица, подписант."""
    rows = []
    for index, line in enumerate(lines, start=1):
        rows.append(
            f'    <СведТов НомСтр="{index}" НаимТов="{escape(line["name"])}" ОКЕИ_Тов="796"'
            f' КолТов="{line["qty"]}" ЦенаТов="{_money(line["price"])}"'
            f' СтТовБезНДС="{_money(line["net"])}" НалСт="{VAT_RATE}%"'
            f' СтТовУчНал="{_money(line["gross"])}">\n'
            f'      <СумНал><СумНал>{_money(line["vat"])}</СумНал></СумНал>\n'
            f'    </СведТов>')
    net = sum(line["net"] for line in lines)
    vat = sum(line["vat"] for line in lines)
    table = "\n".join(rows)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Файл ИдФайл="DP_UPD_{number.replace('/', '_')}" ВерсПрог="Родос-ЭДО 1.0" ВерсФорм="5.03">
  <Документ КНД="1115131" Функция="СЧФДОП" ДатаИнфПр="{issued:%d.%m.%Y}"
            НаимЭконСубСост="{escape(seller['name'])}">
  <СвСчФакт НомерСчФ="{number}" ДатаСчФ="{issued:%d.%m.%Y}" КодОКВ="643">
    <СвПрод>
      <ИдСв><СвЮЛУч НаимОрг="{escape(seller['name'])}" ИННЮЛ="{seller['inn']}" КПП="{seller['kpp']}"/></ИдСв>
      <Адрес><АдрИнф АдрТекст="{escape(seller['address'])}" КодСтр="643"/></Адрес>
    </СвПрод>
    <СвПокуп>
      <ИдСв><СвЮЛУч НаимОрг="{escape(buyer['name'])}" ИННЮЛ="{buyer['inn']}" КПП="{buyer['kpp']}"/></ИдСв>
      <Адрес><АдрИнф АдрТекст="{escape(buyer['address'])}" КодСтр="643"/></Адрес>
    </СвПокуп>
    <ДокПодтвОтгр РеквНаимДок="Договор" РеквНомерДок="{contract['number']}"
                  РеквДатаДок="{contract['signed']:%d.%m.%Y}"/>
    <ИнфПолФХЖ1>
      <ТекстИнф Идентиф="УсловияОплаты" Значение="{escape(str(contract.get('payment_terms', '')))}"/>
    </ИнфПолФХЖ1>
  </СвСчФакт>
  <ТаблСчФакт>
{table}
    <ВсегоОпл СтТовБезНДСВсего="{_money(net)}" СтТовУчНалВсего="{_money(net + vat)}">
      <СумНалВсего><СумНал>{_money(vat)}</СумНал></СумНалВсего>
    </ВсегоОпл>
  </ТаблСчФакт>
  <СвПродПер>
    <СвПер СодОпер="Товары переданы" ДатаПер="{issued:%d.%m.%Y}"/>
  </СвПродПер>
  <Подписант ОблПолн="0" Статус="1" ОснПолн="Должностные обязанности">
    <ЮЛ Должн="{escape(signer)}"/>
  </Подписант>
  </Документ>
</Файл>"""


def _sale_lines(world: World, customer: dict[str, Any], seed: str) -> list[dict[str, Any]]:
    rng = _rng(seed)
    items = [item for item in world.products["items"]
             if item["part"] in {part["drawing_no"] for part in world.parts
                                 if customer["key"] in (part.get("customers") or [])}]
    items = items or world.products["items"]
    chosen = rng.sample(items, k=min(len(items), rng.randint(1, 3)))
    parts = world.by_key("parts")
    lines = []
    for item in chosen:
        qty = rng.randrange(10, 260, 10)
        price = float(item["price"])
        net = qty * price
        vat = round(net * VAT_RATE / 100, 2)
        lines.append({
            "name": f"{parts[item['part']]['name']}, черт. {item['part']} (арт. {item['sku']})",
            "qty": qty, "price": price, "net": net, "vat": vat, "gross": net + vat,
        })
    return lines


def _purchase_lines(world: World, supplier: dict[str, Any], seed: str) -> list[dict[str, Any]]:
    rng = _rng(seed)
    materials = [item for item in world.materials_flat if item.get("supplier") == supplier["key"]]
    lines = []
    for material in materials[:rng.randint(1, 2)] or materials[:1]:
        qty = rng.randrange(20, 900, 10)
        price = float(material.get("price_rub", 0))
        net = qty * price
        vat = round(net * VAT_RATE / 100, 2)
        lines.append({
            "name": material.get("grade") or material.get("name", supplier["supplies"][0]),
            "qty": qty, "price": price, "net": net, "vat": vat, "gross": net + vat,
        })
    return lines


def upd(world: World, root: Path | None = None) -> list[Path]:
    """УПД по реализации и по закупкам — основной поток ЭДО."""
    sites = world.by_key("sites")
    parties = world.by_key("counterparties")
    written: list[Path] = []
    sale_contracts = [c for c in world.contracts if c["kind"] in {"sale", "dealer"}]
    purchase_contracts = [c for c in world.contracts if c["kind"] == "purchase"]

    plan: list[tuple[str, dict[str, Any]]] = (
        [("sale", contract) for contract in sale_contracts]
        + [("purchase", contract) for contract in purchase_contracts])

    for index, (kind, contract) in enumerate(plan):
        number = f"УПД-2026-{index + 101:04d}"
        doc_id = f"UPD-2026-{index + 101:04d}"
        issued = UPD_START + timedelta(days=index * 11)
        party = parties[contract["party"]]
        site = sites["tolyatti"] if kind == "sale" else sites["kovrov"]
        if kind == "sale":
            seller, buyer = _org(site), _party(party)
            lines = _sale_lines(world, party, doc_id)
            signer = "Начальник отдела продаж"
        else:
            seller, buyer = _party(party), _org(site)
            lines = _purchase_lines(world, party, doc_id)
            signer = "Начальник отдела снабжения"
        if not lines:
            continue
        net = sum(line["net"] for line in lines)
        vat = sum(line["vat"] for line in lines)
        card = {
            "doc_id": doc_id,
            "doc_type": "upd",
            "title": f"Универсальный передаточный документ № {number} от {issued:%d.%m.%Y}",
            "org_unit": "Бухгалтерия",
            "spaces": ["finance"],
            "confidentiality": "internal",
            "status": "active",
            "format": "xml",
            "channel": "edo",
            "approved_at": issued,
            "counterparty": party["name"],
            "counterparty_inn": party["inn"],
            "contract": contract["number"],
            "payment_terms": contract.get("payment_terms"),
            "direction": "реализация" if kind == "sale" else "закупка",
            "amount_net_rub": round(net, 2),
            "amount_vat_rub": round(vat, 2),
            "amount_total_rub": round(net + vat, 2),
            "generated_by": "upd",
        }
        body = _upd_xml(number, issued, seller, buyer, contract, lines, signer)
        written.append(write_source("finance", doc_id, card, body, root))
    return written


def invoices(world: World, root: Path | None = None) -> list[Path]:
    """Счета на оплату: документ, по которому в корпусе спрашивают срок и основание платежа."""
    sites = world.by_key("sites")
    parties = world.by_key("counterparties")
    written: list[Path] = []
    chosen = [c for c in world.contracts if c["kind"] in {"sale", "dealer", "service"}][:8]
    for index, contract in enumerate(chosen):
        doc_id = f"SCH-2026-{index + 201:04d}"
        issued = date(2026, 6, 3) + timedelta(days=index * 9)
        party = parties[contract["party"]]
        site = sites["perm"]
        rng = _rng(doc_id)
        lines = (_sale_lines(world, party, doc_id) if contract["kind"] != "service"
                 else [{"name": str(contract["subject"]).capitalize(), "qty": 1,
                        "price": float(rng.randrange(80000, 400000, 5000)), "net": 0.0,
                        "vat": 0.0, "gross": 0.0}])
        if contract["kind"] == "service":
            line = lines[0]
            line["net"] = line["qty"] * line["price"]
            line["vat"] = round(line["net"] * VAT_RATE / 100, 2)
            line["gross"] = line["net"] + line["vat"]
        net = sum(line["net"] for line in lines)
        vat = sum(line["vat"] for line in lines)
        due = issued + timedelta(days=5)

        body = [
            "## 1. Реквизиты для оплаты\n",
            "| Поле | Значение |",
            "| --- | --- |",
            f"| Поставщик | {site['legal_name']} |",
            f"| ИНН / КПП | {site['inn']} / {site['kpp']} |",
            f"| Банк | {site['bank']['name']} |",
            f"| БИК | {site['bank']['bik']} |",
            f"| Расчётный счёт | {site['bank']['account']} |",
            f"| Корреспондентский счёт | {site['bank']['corr_account']} |",
            f"| Покупатель | {party['name']}, ИНН {party['inn']} |",
            f"| Основание | договор {contract['number']} от {contract['signed']:%d.%m.%Y} |\n",
            "## 2. Предмет счёта\n",
            "| № | Наименование | Кол-во | Цена, ₽ | Сумма без НДС, ₽ |",
            "| --- | --- | --- | --- | --- |",
        ]
        for position, line in enumerate(lines, start=1):
            body.append(f"| {position} | {line['name']} | {line['qty']} | {_money(line['price'])} "
                        f"| {_money(line['net'])} |")
        body += [
            "",
            f"2.1. Итого без НДС: {_money(net)} ₽.",
            f"2.2. НДС {VAT_RATE} %: {_money(vat)} ₽.",
            f"2.3. Всего к оплате: {_money(net + vat)} ₽.\n",
            "## 3. Условия оплаты\n",
            f"3.1. Условия оплаты по договору: {contract.get('payment_terms', 'по соглашению сторон')}.",
            f"3.2. Счёт действителен для оплаты до {due:%d.%m.%Y}. После этой даты цена подтверждается "
            "повторно.",
            "3.3. В назначении платежа указывается номер счёта и номер договора. Платёж без указания "
            "основания зачисляется на самый ранний непогашенный долг.",
        ]
        card = {
            "doc_id": doc_id,
            "doc_type": "invoice",
            "title": f"Счёт на оплату № {doc_id.replace('SCH-', 'СЧ-')} от {issued:%d.%m.%Y}",
            "org_unit": "Бухгалтерия",
            "spaces": ["finance"],
            "confidentiality": "internal",
            "status": "active",
            "format": "pdf",
            "channel": "edo",
            "approved_at": issued,
            "approved_by": "Главный бухгалтер",
            "counterparty": party["name"],
            "contract": contract["number"],
            "amount_total_rub": round(net + vat, 2),
            "due_date": due,
            "generated_by": "invoices",
        }
        written.append(write_source("finance", doc_id, card, "\n".join(body), root))
    return written


def service_acts(world: World, root: Path | None = None) -> list[Path]:
    """Акты выполненных работ по сервисным договорам: перевозки, поверка, экспертиза."""
    parties = world.by_key("counterparties")
    sites = world.by_key("sites")
    written: list[Path] = []
    service = [c for c in world.contracts if c["kind"] == "service"]
    months = [(date(2026, month, 28), month) for month in (4, 5, 6, 7, 8)]
    for index, (issued, month) in enumerate(months):
        contract = service[index % len(service)]
        party = parties[contract["party"]]
        doc_id = f"AKT-2026-{index + 301:03d}"
        rng = _rng(doc_id)
        amount = float(rng.randrange(120000, 780000, 5000))
        vat = round(amount * VAT_RATE / 100, 2)
        body = [
            "## 1. Предмет акта\n",
            f"1.1. Исполнитель {party['name']} (ИНН {party['inn']}) выполнил, а заказчик "
            f"{sites['perm']['legal_name']} принял работы по договору {contract['number']} "
            f"от {contract['signed']:%d.%m.%Y}.",
            f"1.2. Отчётный период: {month:02d}.2026.",
            f"1.3. Предмет договора: {contract['subject']}.\n",
            "## 2. Объём и стоимость\n",
            "| Наименование работ | Ед. | Кол-во | Сумма без НДС, ₽ |",
            "| --- | --- | --- | --- |",
            f"| {str(contract['subject']).capitalize()} | усл. | 1 | {_money(amount)} |",
            "",
            f"2.1. НДС {VAT_RATE} %: {_money(vat)} ₽.",
            f"2.2. Всего с НДС: {_money(amount + vat)} ₽.\n",
            "## 3. Приёмка\n",
            "3.1. Работы выполнены в полном объёме и в согласованные сроки. Претензий по объёму, "
            "качеству и срокам заказчик не имеет.",
            f"3.2. Оплата производится в порядке, установленном договором: "
            f"{contract.get('payment_terms', 'по соглашению сторон')}.",
            "3.3. Акт составлен в двух экземплярах, по одному для каждой из сторон, и подписан "
            "усиленной квалифицированной электронной подписью в системе ЭДО.",
        ]
        card = {
            "doc_id": doc_id,
            "doc_type": "service_act",
            "title": f"Акт выполненных работ № {doc_id.replace('AKT-', 'АКТ-')} от {issued:%d.%m.%Y}",
            "org_unit": "Бухгалтерия",
            "spaces": ["finance"],
            "confidentiality": "internal",
            "status": "active",
            "format": "docx",
            "channel": "edo",
            "approved_at": issued,
            "approved_by": "Главный бухгалтер",
            "counterparty": party["name"],
            "contract": contract["number"],
            "amount_total_rub": round(amount + vat, 2),
            "generated_by": "service_acts",
        }
        written.append(write_source("finance", doc_id, card, "\n".join(body), root))
    return written


def reconciliation_acts(world: World, root: Path | None = None) -> list[Path]:
    """Акты сверки взаиморасчётов: таблица оборотов и сальдо на конец периода."""
    parties = world.by_key("counterparties")
    sites = world.by_key("sites")
    written: list[Path] = []
    chosen = [c for c in world.contracts if c["kind"] in {"sale", "purchase"}][:6]
    for index, contract in enumerate(chosen):
        party = parties[contract["party"]]
        doc_id = f"SVERKA-2026H1-{index + 1:02d}"
        rng = _rng(doc_id)
        opening = round(rng.randrange(-900, 2400) * 1000.0, 2)
        rows: list[list[Any]] = []
        balance = opening
        for month in range(1, 7):
            shipped = round(rng.randrange(300, 4200) * 1000.0, 2)
            paid = round(shipped * rng.uniform(0.6, 1.15), 2)
            balance = round(balance + shipped - paid, 2)
            rows.append([f"{month:02d}.2026", shipped, paid, balance])
        table = {
            "name": "Сверка",
            "title": (f"Акт сверки взаимных расчётов между {sites['perm']['legal_name']} и "
                      f"{party['name']} по договору {contract['number']} за 1-е полугодие 2026 г."),
            "columns": ["Период", "Отгружено / поставлено, ₽", "Оплачено, ₽", "Сальдо на конец, ₽"],
            "rows": [["Сальдо на 01.01.2026", "", "", opening], *rows,
                     ["Итого оборот", sum(row[1] for row in rows), sum(row[2] for row in rows), balance]],
        }
        card = {
            "doc_id": doc_id,
            "doc_type": "reconciliation_act",
            "title": f"Акт сверки взаимных расчётов с {party['name']} за 1-е полугодие 2026 г.",
            "org_unit": "Бухгалтерия",
            "spaces": ["finance"],
            "confidentiality": "internal",
            "status": "active",
            "format": "xlsx",
            "channel": "edo",
            "approved_at": date(2026, 7, 10),
            "approved_by": "Главный бухгалтер",
            "counterparty": party["name"],
            "contract": contract["number"],
            "balance_rub": balance,
            "generated_by": "reconciliation_acts",
        }
        written.append(write_table_source("finance", doc_id, card, table, root))
    return written


GENERATORS = (upd, invoices, service_acts, reconciliation_acts)
