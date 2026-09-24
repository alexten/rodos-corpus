.PHONY: check lint test build repro

check: lint test repro

lint:
	uv run ruff check .
	uv run mypy
	uv run rodos-corpus lint
	uv run rodos-corpus verify

test:
	uv run pytest -q

# Гейт воспроизводимости (ADR-0011): пересборка обязана давать те же байты.
# Гонять надо И генерацию, И рендеринг: проверка одного рендеринга зелёная при
# недетерминированном генераторе — она просто не доходит до места поломки.
repro:
	uv run --extra build rodos-corpus generate
	uv run --extra build rodos-corpus render
	uv run rodos-corpus manifest
	git diff --exit-code
