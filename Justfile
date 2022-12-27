# This is the main Justfile for the Fixie SDK repo.
# To install Just, see: https://github.com/casey/just#installation 

# This causes the .env file to be read by Just.
set dotenv-load := true

# Allow for positional arguments in Just receipes.
set positional-arguments := true

# Default recipe that runs if you type "just".
default: format check test

# Install dependencies for local development.
install:
    pip install poetry
    poetry install --sync
    poetry run mypy --install-types --non-interactive .

# Format code.
format:
    poetry run autoflake . --remove-all-unused-imports --quiet --in-place -r --exclude third_party
    poetry run isort . --force-single-line-imports
    poetry run black .

# Run code formatting and type checks.
check:
    poetry run black . --check
    poetry run isort . --check --force-single-line-imports
    poetry run autoflake . --check --quiet --remove-all-unused-imports -r --exclude third_party
    poetry run mypy .

# Run all tests.
test PATH=".":
    poetry run pytest --ignore third_party {{PATH}}

# Run tests with verbose output.
test-verbose PATH=".":
    poetry run pytest --ignore third_party -vv --log-cli-level=INFO {{PATH}}

# Run a Python REPL in the Poetry environment.
python:
    poetry run python

# Run the poetry command with the local .env loaded.
poetry *FLAGS:
    poetry {{FLAGS}}

# Run a new shell with the Poetry Pyenv environment and .env file loaded.
shell:
    poetry shell

