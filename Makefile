# RAGOPS Makefile
# Production-Ready RAG Pipeline

.PHONY: help install start stop restart logs status health test clean dev

# Default target
help: ## Show this help message
	@echo "RAGOPS - Production-Ready RAG Pipeline"
	@echo "======================================"
	@echo "Available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install and configure the system
	@echo "🚀 Installing RAGOPS..."
	@if [ ! -f .env ]; then cp .env.example .env && echo "📝 Created .env file - please configure your API keys"; fi
	@docker compose pull
	@echo "✅ Installation complete! Please configure .env with your API keys."

start: ## Start all services
	@echo "🚀 Starting RAGOPS services..."
	@docker compose up -d
	@echo "⏳ Waiting for services to be ready..."
	@sleep 10
	@make status

stop: ## Stop all services  
	@echo "🛑 Stopping RAGOPS services..."
	@docker compose down

restart: ## Restart all services
	@echo "🔄 Restarting RAGOPS services..."
	@docker compose restart
	@sleep 5
	@make status

logs: ## View logs from all services
	@docker compose logs -f

status: ## Check status of all services
	@echo "📊 Service Status:"
	@docker compose ps
	@echo ""
	@make health

health: ## Check health of all services
	@echo "🏥 Health Checks:"
	@echo -n "Backend API: "
	@curl -s http://localhost:18000/health >/dev/null 2>&1 && echo "✅ Healthy" || echo "❌ Unhealthy"
	@echo -n "Meilisearch: "
	@curl -s http://localhost:7700/health >/dev/null 2>&1 && echo "✅ Healthy" || echo "❌ Unhealthy"

test: ## Run system validation tests
	@echo "🧪 Running system validation..."
	@docker compose exec backend python final_rag_test_report.py

demo: ## Run feature demonstration
	@echo "🎬 Running feature demo..."
	@docker compose exec backend python demo_working_features.py

ingest: ## Ingest sample documents
	@echo "📥 Ingesting sample documents..."
	@docker compose exec backend python ingest.py

dev: ## Start in development mode with live reload
	@echo "🛠️  Starting in development mode..."
	@docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

build: ## Build all container images
	@echo "🔨 Building container images..."
	@docker compose build

clean: ## Clean up containers, volumes, and images
	@echo "🧹 Cleaning up..."
	@docker compose down -v
	@docker system prune -f
	@echo "✅ Cleanup complete"

backup: ## Backup Meilisearch data
	@echo "💾 Creating backup..."
	@docker compose exec meilisearch sh -c "tar czf - /meili_data" > backup_$(shell date +%Y%m%d_%H%M%S).tar.gz
	@echo "✅ Backup created"

# API Testing shortcuts
api-health: ## Test API health endpoint
	@curl -s http://localhost:18000/health | jq .

api-docs: ## Open API documentation
	@echo "📚 Opening API documentation at http://localhost:18000/docs"
	@python -m webbrowser http://localhost:18000/docs 2>/dev/null || echo "Visit: http://localhost:18000/docs"

search-test: ## Test search functionality
	@echo "🔍 Testing search..."
	@curl -X POST "http://localhost:18000/search" \
		-H "Content-Type: application/json" \
		-d '{"query": "What is this system about?", "k": 3}' | jq .

chat-test: ## Test chat functionality  
	@echo "💬 Testing chat..."
	@curl -X POST "http://localhost:18000/chat" \
		-H "Content-Type: application/json" \
		-d '{"messages": [{"role": "user", "content": "Hello! How are you?"}]}' | jq .

# Development helpers
shell-backend: ## Open shell in backend container
	@docker compose exec backend bash

shell-meilisearch: ## Open shell in meilisearch container
	@docker compose exec meilisearch sh

logs-backend: ## View backend logs
	@docker compose logs -f backend

logs-meilisearch: ## View meilisearch logs
	@docker compose logs -f meilisearch

logs-litellm: ## View litellm logs
	@docker compose logs -f litellm

# Production helpers
prod-start: ## Start in production mode
	@echo "🚀 Starting in production mode..."
	@docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

scale-backend: ## Scale backend service (usage: make scale-backend n=3)
	@docker compose scale backend=$(or $(n),2)
	@echo "⚖️  Backend scaled to $(or $(n),2) instances"

monitor: ## Show resource usage
	@docker stats

# Quick setup for new users
quick-start: install start ingest demo ## Complete quick start setup
	@echo ""
	@echo "🎉 RAGOPS is ready!"
	@echo "📚 API Docs: http://localhost:18000/docs"
	@echo "🔍 Test search: make search-test"
	@echo "💬 Test chat: make chat-test"
	@echo "📊 Check status: make status"
