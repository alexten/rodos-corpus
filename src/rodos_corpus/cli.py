"""Командная строка корпуса: `rodos-corpus <команда>`."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from rodos_corpus import integrity, paths


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        "rodos-corpus", description="модель мира и демо-корпус ГК «Родос-Деталь»")
    commands = parser.add_subparsers(dest="command", required=True, metavar="команда")
    commands.add_parser("lint", help="согласованность мира, исходников и фиктивность реквизитов")
    generate = commands.add_parser("generate", help="породить исходники документов из модели мира")
    generate.add_argument("names", nargs="*", help="только эти генераторы")
    render = commands.add_parser("render", help="отрендерить исходники в DOCX/PDF/XLSX/EML/XML и карточки")
    render.add_argument("--space")
    render.add_argument("--only", help="один документ по идентификатору")
    commands.add_parser("stats", help="состав корпуса: документы по пространствам, типам и форматам")
    commands.add_parser("manifest", help="пересобрать MANIFEST.json по карточкам")
    commands.add_parser("verify", help="сверить файлы с описью")
    where = commands.add_parser("path", help="пути внутри установленного пакета")
    where.add_argument("what", nargs="?", default="data",
                       choices=["data", "world", "corpus", "source", "rendered", "cards", "stream", "fonts"])
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "lint":
        from rodos_corpus.lint import main as lint_main
        return lint_main()
    if args.command == "generate":
        from rodos_corpus.generators.run import run
        return run(args.names or None)
    if args.command == "render":
        from rodos_corpus.build import render_all
        return render_all(args.space, args.only)
    if args.command == "stats":
        from rodos_corpus.build import stats
        return stats()
    if args.command == "manifest":
        return integrity.write()
    if args.command == "verify":
        problems = integrity.verify()
        for problem in problems:
            print(problem)
        print(f"расхождений: {len(problems)}")
        return 1 if problems else 0
    if args.command == "path":
        print(getattr(paths, f"{args.what}_root" if args.what != "data" else "data_root")())
        return 0
    return 1
