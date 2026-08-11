.PHONY: up down build logs ps restart test health help

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

ps:
	docker compose ps

restart:
	docker compose restart

test:
	cd backend/api && uv run pytest
	cd backend/database && uv run pytest

health:
	curl -sf http://127.0.0.1:8004/health
	curl -sf http://127.0.0.1:8005/health
	curl -sf http://127.0.0.1:3000/

help:
	@echo "anon-feedback Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  up        Start the stack: docker compose up -d"
	@echo "  down      Stop the stack: docker compose down"
	@echo "  build     Build images: docker compose build"
	@echo "  logs      Follow logs: docker compose logs -f"
	@echo "  ps        Show stack status: docker compose ps"
	@echo "  restart   Restart services: docker compose restart"
	@echo "  test      Run pytest in backend/api and backend/database (requires uv)"
	@echo "  health    Curl the /health endpoints of api and database"
	@echo "  help      Show this help"
	@echo ""
	@echo "Prerequisites: docker, docker compose, uv, curl"
