## options
# based on https://tech.davis-hansson.com/p/make/
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:
.DEFAULT_GOAL := help
.DELETE_ON_ERROR:

## variables
SOURCE_DIR = tests

## formula

# based on https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
.PHONY: help
help:  ## print help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

## dependencies

.PHONY: setup
setup: ## Setup repository
	pip install poetry pre-commit
	if [ -d .git ]; then pre-commit install; else echo "Current directory isn't a git project, skipping pre-commit installation" ; fi
	brew update && brew install postgresql@15
	brew link postgresql@15

.PHONY: lock
lock: ## Update lock file
	poetry lock --no-update

## checks

.PHONY: format
format: ## run lint and auto code formatting
	python -m ruff check --fix .
	python -m ruff format .

.PHONY: lint
lint: ## run lint
	python -m ruff check .
	python -m ruff format .

.PHONY: test
test: ## run unit tests
	python -m pytest $(SOURCE_DIR) --cov $(SOURCE_DIR) --cov-report xml:coverage.xml --cov-report term --junitxml=junit.xml

## app

.PHONY: dev
dev: ## run app with hot reload
	python -m uvicorn app.server:app --reload --port 8088

.PHONY: run
run: ## run app
	python -m gunicorn app.server:app -c scripts/gunicorn_conf.py
