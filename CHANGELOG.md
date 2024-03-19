# Changelog

## v1.2.0 (2024-03-19)

- Fixed the type signatures of `typenames` and `parse_type_tree` to reflect the typing of input type annotations, according to static type checkers. ([PR #6](https://github.com/jayqi/typenames/pull/6))
- Added [PEP 561 `py.typed` marker file](https://peps.python.org/pep-0561/#packaging-type-information) to indicate that the package supports type checking. ([PR #6](https://github.com/jayqi/typenames/pull/6))

## v1.1.0 (2024-03-08)

- Changed `REMOVE_ALL_MODULES`'s regex pattern to also remove `<locals>` from rendered output. `<locals>` typically appears in a type's qualified name if the type was defined within the local scope of a function or class method. ([PR #4](https://github.com/jayqi/typenames/pull/4))
- Removed support for Python 3.7. ([PR #5](https://github.com/jayqi/typenames/pull/5))
- Deprecated `LITERAL_TYPE_SUPPORTED` flag, since typenames no longer supports Python versions where this is false. ([PR #5](https://github.com/jayqi/typenames/pull/5))

## v1.0.0 (2023-02-20)

Initial release! 🎉
