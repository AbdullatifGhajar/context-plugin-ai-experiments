.ONESHELL:
ENV=env
PYTHON=$(ENV)/bin/python3
PRE_COMMIT=$(ENV)/bin/pre-commit
PIP=$(ENV)/bin/pip
PYTEST=$(ENV)/bin/pytest

.PHONY: create-env
create-env:			## Create environment
	@echo "Creating environment"
	@python3 -m venv $(ENV)

.PHONY: install
install:			## Install requirements
	@echo "Installing requirements"
	@$(PIP) install -r requirements.txt

.PHONY: setup
setup: create-env install	## Create or update conda environment and install pre-commits
	@echo "Installing pre-commit hooks"
	@$(PIP) install pre-commit black isort flake8 pyproject-flake8 mypy pytest
	@$(PRE_COMMIT) pre-commit autoupdate
	@$(PRE_COMMIT) install-hooks
	@$(PRE_COMMIT) install

.PHONY: lint
lint:				## Lint code using pre-commits
	@$(PRE_COMMIT) run --all-files

.PHONY: test
test:				## Run tests
	@$(PYTEST)


.PHONY: help
help:            		## Show the help
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@fgrep "##" Makefile | fgrep -v fgrep
