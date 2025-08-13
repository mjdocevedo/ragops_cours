up:
	clear && echo "Starting services..."
	docker compose up -d

down:
	docker compose down -v --remove-orphans

logs:
	docker compose logs -f

restart: down up

ps:
	docker compose ps

status: ps logs

status-api:
	curl http://localhost:18000/health