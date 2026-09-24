"""Демо-корпус вымышленной ГК «Родос-Деталь»: модель мира и документы предприятия.

Пакет отдаёт данные, а не сервис. Всё, что нужно потребителю, — здесь:

    from rodos_corpus import World, load_all, rendered_root, rendered_path, manifest

Документы лежат отрендеренными в семи форматах и коммитятся в репозиторий: приложение начинает
работать сразу после установки, без ключей API и без генерации на лету (ADR-0008). Пересборка
обязана давать те же байты (ADR-0011), иначе прогоны оценки перестают быть сравнимыми.

**Предприятие вымышлено.** Все реквизиты начинаются с `00` — такой префикс невозможен ни у
настоящего ИНН, ни у КПП, ОГРН, БИК или расчётного счёта; это проверяет линтер, а не декларация.
"""

from rodos_corpus.integrity import CORPUS_VERSION, manifest, verify
from rodos_corpus.paths import (
    cards_root,
    corpus_root,
    data_root,
    fonts_root,
    rendered_path,
    rendered_root,
    source_root,
    stream_root,
    world_root,
)
from rodos_corpus.source import SourceDoc, load_all, parse, validate
from rodos_corpus.world import World

__all__ = [
    "CORPUS_VERSION", "SourceDoc", "World",
    "cards_root", "corpus_root", "data_root", "fonts_root", "load_all", "manifest",
    "parse", "rendered_path", "rendered_root", "source_root", "stream_root",
    "validate", "verify", "world_root",
]
