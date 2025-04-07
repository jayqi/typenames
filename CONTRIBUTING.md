# Contributing to typenames

[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![types - mypy](https://img.shields.io/badge/types-mypy-blue.svg)](https://github.com/python/mypy)

## Report a bug or request a feature

Please file an issue in the [issue tracker](https://github.com/drivendataorg/typenames/issues).

## External contributions

Pull requests from external contributors are welcome. However, we ask that any nontrivial changes be discussed with maintainers in an [issue](https://github.com/drivendataorg/typenames/issues) first before submitting a pull request.

## Developers guide

This project uses [uv](https://docs.astral.sh/uv/) as its project management tool and [Just](https://github.com/casey/just) as a task runner.

### Create development environment

```bash
just sync
```

### Tests

```bash
just test
```

You can run the tests for a specific Python version with, for example:

```bash
just python=3.12 test
```

To run tests on all supported Python versions, run:

```bash
just test-all
```

### Type annotation inspection notebooks

The directory [`inspect_types/`](./inspect_types/) contains Jupyter notebooks for each supported Python version that inspects attributes and behavior of various type annotations. These are intended as a development aide for understanding behavior of different annotations in different versions of Python.

There are Just commands for regenerating these notebooks by running `jupyter nbconvert` in an isolated environment. To regenerate a notebook for a specific Python version, run for example:

```bash
just python=3.12 inspect-types
```

To regenerate notebooks for all supported Python versions, run:

```bash
just inspect-types-all
```
