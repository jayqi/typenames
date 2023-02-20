# typenames : String representations of type annotations

typenames is a configurable Python library for creating string representations of type annotations. By default, it produces compact representations by removing standard library module names. Additional configurable options include standardizing on `|` operator syntax for unions or standard collections classes for generics.

```python
import typing
from typenames import typenames

typenames(int)
#> 'int'
typenames(dict[str, typing.Any])
#> 'dict[str, Any]'
typenames(str | int)
#> 'str | int'
typenames(typing.Optional[str])
#> 'Optional[str]'
```

## Why use this library?

String representations of Python type objects, type aliases, and special typing forms are inconsistent and verbose. Here are some comparisons using default settings against built-in string representations:

| Input | `str(...)` | `typenames(...)` |
| :-: | :-: | :-: |
| `int` | `<class 'int'>` | `int` |
| `list` | `<class 'list'>` | `list` |
| `typing.Optional[int]` | `typing.Optional[int]` | `Optional[int]` |
| `collections.abc.Iterator[typing.Any]` | `collections.abc.Iterator[typing.Any]` | `Iterator[Any]` |

typenames also has handy configurable functionality, such as:

- Forcing standardization on `|` operator union syntax (e.g., `Union[int, str]` to `int | str`) or vice versa
- Forcing standardization on `|` operator optional syntax (e.g., `Optional[int]` to `int | None`) or vice versa
- Forcing standardization on standard collection types for generics (e.g., `List[int]` to `list[int]`) or vice versa
- Controlling exactly which module names to remove using regex patterns.

No need for string manipulation to get what you want!

## Installation

typenames is available on PyPI:

```bash
pip install typenames
```

## Basic Usage

The main way to use the library is the `typenames` function. Calling it on a type annotation produces string annotations

```python
import typing
from typenames import typenames

typenames(int)
#> 'int'
typenames(typing.Optional[str])
#> 'Optional[str]'
typenames(collections.abc.Callable[[int], tuple[str, ...]])
#> 'Callable[[int], tuple[str, ...]]
```

Under the hood, typenames parses a type annotation as a tree structure. If you need to see the parsed tree, using the `parse_type_tree` function.

```python
import typing
from typenames import parse_type_tree

parse_type_tree(typing.Any | list[typing.Any])
#> <GenericNode typing.Union[<TypeNode typing.Any>, <GenericNode <class 'list'>[<TypeNode typing.Any>]>]>
```

## Configurable options

### Union Syntax (`union_syntax`)

### Optional Syntax (`optional_syntax`)

### Standard Collections Syntax (`standard_collections_syntax`)
