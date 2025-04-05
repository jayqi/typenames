python := "3.13"

# Print this help documentation
help:
    just --list

# Sync requirements
sync:
    uv sync

# Run linting
lint:
    uv run ruff format --check
    uv run ruff check

# Run formatting
format:
    uv run ruff format
    uv run ruff check --fix

# Run static typechecking
typecheck:
    uv run --python {{python}} --no-dev --group typecheck --isolated \
        mypy typenames tests/typechecks.py --install-types --non-interactive

# Run the tests
test *args:
    uv run --python {{python}} --isolated --no-editable --no-dev --group tests --reinstall \
        python -I -m pytest {{args}}

# Run all tests with Python version matrix
test-all:
    for python in 3.9 3.10 3.11 3.12 3.13; do \
        just python=$python test; \
    done

# Generate notebook that inspects types
inspect-types:
    uv run --python {{python}} --isolated --only-group inspect-types \
        jupyter nbconvert inspect_types/_inspect_types.ipynb \
            --to notebook \
            --output inspect_types_{{python}}.ipynb \
            --execute \
            --allow-errors

# Generate notebook that inspects types for all Python versions
inspect-types-all:
    for python in 3.9 3.10 3.11 3.12 3.13; do \
        just python=$python inspect-types; \
    done
