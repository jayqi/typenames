# Contributing to testnames

[![Hatch project](https://img.shields.io/badge/%F0%9F%A5%9A-Hatch-4051b5.svg)](https://github.com/pypa/hatch) [![linting - Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v0.json)](https://github.com/charliermarsh/ruff) [![code style - black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![types - mypy](https://img.shields.io/badge/types-mypy-blue.svg)](https://github.com/python/mypy)

## Report a bug or request a feature

Please file an issue in the [issue tracker](https://github.com/jayqi/typenames/issues).

## Developers guide

This project uses [Hatch](https://github.com/pypa/hatch) as its project management tool.

### Tests

To run tests in your current environment, you should install from source with the `tests` extra to additionally install test dependencies (pytest). Then, use pytest to run the tests.

```bash
# Install with test dependencies
pip install .[tests]
# Run tests
pytest tests.py
```

To run tests on the full test matrix, you should use Hatch:

```bash
hatch run tests:run
```

### Type annotation inspection notebooks

The directory [`inspect_types/`](./inspect_types/) contains Jupyter notebooks for each supported Python version that inspects attributes and behavior of various type annotations. These are intended as a development aide for understanding behavior of different annotations in different versions of Python.

To regenerate these notebooks, run:

```bash
hatch run inspect-types:generate-notebook
```

This command will run `nbconvert` on the configured Python version matrix in isolated environments.
