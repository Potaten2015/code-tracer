PYTHON_BINARY := python3
VIRTUAL_ENV := venv
VIRTUAL_BIN := $(VIRTUAL_ENV)/bin
PROJECT_NAME := code_tracer

## help - Display help about make targets for this Makefile
help:
	@cat Makefile | grep '^## ' --color=never | cut -c4- | sed -e "`printf 's/ - /\t- /;'`" | column -s "`printf '\t'`" -t

## build - Builds the project in preparation for release
build:
	$(VIRTUAL_BIN)/python -m build

## clean - Remove the virtual environment and clear out .pyc files
clean:
	rm -rf $(VIRTUAL_ENV) dist *.egg-info
	find . -name '*.pyc' -delete

## black - Runs the Black Python formatter against the project
black:
	$(VIRTUAL_BIN)/black $(PROJECT_NAME)/

## black-check - Checks if the project is formatted correctly against the Black rules
black-check:
	$(VIRTUAL_BIN)/black $(PROJECT_NAME)/ --check

## format - Runs all formatting tools against the project
format: black isort lint

## format-check - Checks if the project is formatted correctly against all formatting rules
format-check: black-check isort-check lint

## install - Install the project locally
install:
	$(PYTHON_BINARY) -m venv $(VIRTUAL_ENV)
	$(VIRTUAL_BIN)/pip install -e ."[dev]"

## isort - Sorts imports throughout the project
isort:
	$(VIRTUAL_BIN)/isort $(PROJECT_NAME)/

## isort-check - Checks that imports throughout the project are sorted correctly
isort-check:
	$(VIRTUAL_BIN)/isort $(PROJECT_NAME)/ --check-only

## lint - Lint the project
lint:
	$(VIRTUAL_BIN)/flake8 $(PROJECT_NAME)/

.PHONY: help build clean black black-check format format-check install isort isort-check lint
