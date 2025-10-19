## options
# based on https://tech.davis-hansson.com/p/make/
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:
.DEFAULT_GOAL := help
.DELETE_ON_ERROR:
SOURCE_DIR = zion
TEST_DIR ?= zion

## formula

# based on https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
.PHONY: help
help:  ## print help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

## dependencies

.PHONY: deps-install-python
deps-install-python:
	poetry install --no-root
	pip list

.PHONY: install-hooks
install-hooks:
	python -m pre_commit install --install-hooks
	wget -O .git/hooks/prepare-commit-msg https://raw.githubusercontent.com/commitizen-tools/commitizen/master/hooks/prepare-commit-msg.py
	chmod +x .git/hooks/prepare-commit-msg
	wget -O .git/hooks/post-commit https://raw.githubusercontent.com/commitizen-tools/commitizen/master/hooks/post-commit.py
	chmod +x .git/hooks/post-commit

.PHONY: deps-install
deps-install: deps-install-python install-hooks ## install dependencies

.PHONY: deps-update
deps-update:
	poetry update
	poetry export --format requirements.txt --output requirements.txt --without-hashes
	python -m pre_commit autoupdate

requirements.txt: poetry.lock
	poetry export --format requirements.txt --output requirements.txt --without-hashes

requirements-dev.txt: poetry.lock
	poetry export --with dev --format requirements.txt --output requirements-dev.txt --without-hashes

## checks

.PHONY: format
format: ## run lint and auto fix the format
	poetry run python -m ruff check --fix .
	poetry run python -m ruff format .

.PHONY: lint
lint: ## run lint
	poetry run python -m ruff check .
	poetry run python -m ruff format .
	# poetry run python -m mypy $(SOURCE_DIR)

.PHONY: test
test: ## run unit tests
	python -m pytest $(TEST_DIR) --cov $(SOURCE_DIR) --cov-report xml:coverage.xml --cov-report term --junitxml=junit.xml

.PHONY: run-ci
run-ci: deps-install-python lint test  ## run ci

## app

.PHONY: dev
dev: ## run app with hot reload
	python -m uvicorn zion.main:app --reload

.PHONY: run
run: ## run app
	python -m gunicorn zion.main:app -c zion/gunicorn_conf.py

.PHONY: playground
playground: ## run playground
	python playground/main.py

.PHONY: setup-pre-commit
setup-pre-commit: ## setup pre-commit hooks
	python -m pre_commit install
