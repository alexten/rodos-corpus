"""Где лежат данные корпуса.

Данные едут внутри пакета (`src/rodos_corpus/data/`), а не в корне репозитория: тогда установка
колесом и установка editable дают одни и те же пути, и потребителю не приходится гадать, от чего
отсчитывать. Всё остальное в пакете обращается к каталогам только отсюда.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def data_root() -> Path:
    """Корень данных: от него отсчитываются поля `source` и `rendered` в карточках."""
    return Path(__file__).resolve().parent / "data"


def world_root() -> Path:
    return data_root() / "world"


def corpus_root() -> Path:
    return data_root() / "corpus"


def source_root() -> Path:
    return corpus_root() / "source"


def rendered_root() -> Path:
    """Каталог отрендеренных файлов; он же папка выгрузки для `ingest run --corpus`.

    Первый подкаталог под ним — ключ пространства (`production`, `finance`, `sales`, `it`,
    `common`, плюс `_pii`): по нему приём берёт подсказку «как минимум это пространство».
    Раскладку менять нельзя, не сломав маршрутизацию у потребителя.
    """
    return corpus_root() / "rendered"


def cards_root() -> Path:
    return corpus_root() / "cards"


def stream_root() -> Path:
    """Поток входящих событий: письма и присланные документы с конвертом и датой."""
    return data_root() / "stream"


def fonts_root() -> Path:
    return data_root() / "assets" / "fonts"


def rendered_path(card: dict[str, Any] | str) -> Path:
    """Файл документа по карточке или по идентификатору.

    Карточка хранит `rendered` относительно корня данных (`corpus/rendered/<space>/<файл>`),
    и это та же строка, что была в репозитории ассистента, — поэтому карточки при выносе
    корпуса не поменялись ни на байт.
    """
    if isinstance(card, str):
        import yaml
        loaded: dict[str, Any] = yaml.safe_load((cards_root() / f"{card}.yaml").read_text(encoding="utf-8"))
    else:
        loaded = card
    return data_root() / str(loaded["rendered"])
