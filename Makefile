.PHONY: setup lint test run playground mcp

setup:
	uv sync

lint:
	uv run ruff check .
	uv run ruff format .

test:
	uv run pytest tests/

playground:
	uv run adk web app --host 127.0.0.1 --port 18081 --reload_agents

mcp:
	uv run python app/mcp_server.py
