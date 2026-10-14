.PHONY: help dev test docs clean build deploy

help: ## Show available commands
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: ## Start development environment
	docker-compose up -d
	docker-compose logs -f

clean: ## Remove containers and volumes
	docker-compose down -v
	rm -rf __pycache__ */__pycache__ */*/__pycache__

build: ## Build all Docker images
	docker-compose build --no-cache

test: ## Run test suite
	pytest tests/ -v --cov=. --cov-report=html

test-unit: ## Run unit tests only
	pytest tests/unit/ -v --cov=.

test-integration: ## Run integration tests
	pytest tests/integration/ -v

test-load: ## Run load tests
	locust -f tests/load/load_test.py --host=http://localhost:8000

lint: ## Run linters
	black .
	isort .
	flake8 .
	mypy .

format: ## Format code
	black .
	isort .

docs: ## Generate documentation
	sphinx-build -b html docs/ docs/_build/html

deploy-dev: ## Deploy to development environment
	kubectl apply -f kubernetes/
	helm upgrade --install rec-engine ./terraform/aws

deploy-prod: ## Deploy to production environment
	kubectl apply -f kubernetes/production/
	helm upgrade --install rec-engine-prod ./terraform/aws --set environment=production

tf-plan: ## Generate Terraform plan
	cd terraform/aws && terraform plan

tf-apply: ## Apply Terraform configuration
	cd terraform/aws && terraform apply -auto-approve

tf-destroy: ## Destroy Terraform infrastructure
	cd terraform/aws && terraform destroy -auto-approve

seed-data: ## Seed database with sample data
	docker-compose exec backend python -m ml.inference.seed_data

create-db-migrations: ## Create new database migration
	docker-compose exec backend alembic revision --autogenerate -m "migration_message"

run-dag: ## Run specific Airflow DAG
	docker-compose exec airflow-scheduler airflow dags trigger dag_name

monitoring: ## Start monitoring stack
	docker-compose up -d prometheus grafana

scala-tests: ## Run Scala/Kafka stream tests
	kafka-topics --bootstrap-server localhost:9092 --list

spark-jobs: ## Run Spark jobs
	docker-compose exec spark-master yarn job --master local[*] ./spark/jobs/*.py

setup-env: ## Set up local development environment
	@echo "Setting up environment..."
	cp .env.example .env
	echo "Environment setup complete!"
