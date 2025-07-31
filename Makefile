# Thai Tokenizer for MeiliSearch - Quick Commands

.PHONY: help setup-existing start-dev test clean

help: ## Show this help message
	@echo "🚀 Thai Tokenizer for MeiliSearch"
	@echo "================================="
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "📚 Documentation:"
	@echo "  README.md           - Main documentation"
	@echo "  QUICK_START.md      - Quick setup guide"

setup-existing: ## Setup Thai Tokenizer with existing MeiliSearch
	@echo "🚀 Setting up Thai Tokenizer with existing MeiliSearch..."
	@bash scripts/setup_existing_meilisearch.sh

start-dev: ## Start development API with compound word support
	@echo "🚀 Starting development API..."
	@python3 scripts/start_api_with_compounds.py

start-full: ## Start full stack (Thai Tokenizer + MeiliSearch)
	@echo "🚀 Starting full stack..."
	@docker compose -f deployment/docker/docker-compose.yml up -d

test: ## Run integration tests
	@echo "🧪 Running integration tests..."
	@python3 tests/integration/test_api_integration.py

test-existing: ## Test existing MeiliSearch integration
	@echo "🧪 Testing existing MeiliSearch integration..."
	@./tests/integration/test_existing_meilisearch_setup.sh

clean: ## Stop all services and clean up
	@echo "🧹 Cleaning up..."
	@docker compose -f deployment/docker/docker-compose.yml down || true
	@docker compose -f deployment/docker/docker-compose.tokenizer-only.yml down || true

install: ## Install Python dependencies
	@echo "📦 Installing dependencies..."
	@pip install -r requirements.txt

build: ## Build Docker images
	@echo "🐳 Building Docker images..."
	@docker compose -f deployment/docker/docker-compose.yml build