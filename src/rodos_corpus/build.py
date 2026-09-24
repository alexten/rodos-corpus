"""Сборка корпуса: рендеринг исходников, карточки, сводка состава."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from rodos_corpus.render import render
from rodos_corpus.source import load_all, validate


def render_all(space: str | None = None, only: str | None = None, root: Path | None = None) -> int:
    docs = load_all(root)
    if space:
        docs = [doc for doc in docs if space in doc.card.get("spaces", [])]
    if only:
        docs = [doc for doc in docs if doc.doc_id == only]
    if not docs:
        print("нечего рендерить")
        return 1
    problems = [problem for doc in docs for problem in validate(doc)]
    for problem in problems:
        print(problem)
    if problems:
        print(f"исходники с ошибками: {len(problems)}")
        return 1
    # Вложения обязаны быть отрендерены раньше письма, которое их прикладывает.
    docs = sorted(docs, key=lambda doc: doc.fmt == "eml")
    for doc in docs:
        _, card = render(doc, root)
        print(f"{doc.doc_id:22s} {doc.fmt:4s} {card['bytes']:7d} Б  {card['title'][:60]}")
    print(f"готово: {len(docs)} документов")
    return 0


def stats(root: Path | None = None) -> int:
    docs = load_all(root)
    if not docs:
        print("корпус пуст")
        return 1
    by_space: Counter[str] = Counter()
    for doc in docs:
        for space in doc.card["spaces"]:
            by_space[space] += 1
    print(f"документов: {len(docs)}")
    print("\nпо пространствам (документ может попадать в несколько):")
    for space, count in by_space.most_common():
        print(f"  {space:12s} {count:4d}")
    print("\nпо типам:")
    for doc_type, count in Counter(doc.card["doc_type"] for doc in docs).most_common():
        print(f"  {doc_type:22s} {count:4d}")
    print("\nпо форматам:")
    for fmt, count in Counter(doc.fmt for doc in docs).most_common():
        print(f"  {fmt:6s} {count:4d}")
    print("\nпо статусам:")
    for status, count in Counter(doc.card["status"] for doc in docs).most_common():
        print(f"  {status:12s} {count:4d}")
    multi = sum(1 for doc in docs if len(doc.card["spaces"]) > 1)
    print(f"\nв нескольких пространствах: {multi}")
    return 0
