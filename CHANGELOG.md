# Changelog

## v2.0.0 (Unreleased)

- Changed the default for [`standard_collection_syntax`](./README.md#standard-collection-syntax-standard_collection_syntax) from `"as_given"` to `"standard_class"`. This change is intended to encourage the use of the standard collection syntax, since all currently supported Python versions support it and the typing module aliases are [deprecated](https://docs.python.org/3/library/typing.html#deprecated-aliases).
- Removed support for Python 3.8.
- Added support for Python 3.13.
- Removed deprecated `LITERAL_TYPE_SUPPORTED` flag. (Deprecated in v1.1.0.)

_Note: the typenames repository has moved to the [drivendataorg](https://github.com/drivendataorg/typenames) GitHub organization. The documentation website has also moved to a [new address](https://typenames.drivendata.org)._

## v1.3.0 (2024-07-16)

- Changed how `typenames` handles type annotations that include `typing.Annotated` or `typing_extensions.Annotated`. ([PR #8](https://github.com/drivendataorg/typenames/pull/8), [Issue #7](https://github.com/drivendataorg/typenames/issues/7))
  - Added `include_extras` configuration option to `typenames` to control whether `Annotated` and metadata should be shown.
  - By default, `include_extras` is `False`, and `Annotated` and extra metadata will _not_ be rendered.

## v1.2.0 (2024-03-19)

- Fixed the type signatures of `typenames` and `parse_type_tree` to reflect the typing of input type annotations, according to static type checkers. ([PR #6](https://github.com/drivendataorg/typenames/pull/6))
- Added [PEP 561 `py.typed` marker file](https://peps.python.org/pep-0561/#packaging-type-information) to indicate that the package supports type checking. ([PR #6](https://github.com/drivendataorg/typenames/pull/6))

## v1.1.0 (2024-03-08)

- Changed `REMOVE_ALL_MODULES`'s regex pattern to also remove `<locals>` from rendered output. `<locals>` typically appears in a type's qualified name if the type was defined within the local scope of a function or class method. ([PR #4](https://github.com/drivendataorg/typenames/pull/4))
- Removed support for Python 3.7. ([PR #5](https://github.com/drivendataorg/typenames/pull/5))
- Deprecated `LITERAL_TYPE_SUPPORTED` flag, since typenames no longer supports Python versions where this is false. ([PR #5](https://github.com/drivendataorg/typenames/pull/5))

## v1.0.0 (2023-02-20)

Initial release! 🎉
