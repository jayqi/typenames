import typing

from typenames import parse_type_tree, typenames

typenames(int)
# Unions
typenames(str | int)
typenames(typing.Union[str, int])
typenames(typing.Optional[str])
# Generics
typenames(dict[str, int])
typenames(typing.Dict[str, int])
# Other special forms
typenames(typing.Any)
typenames(typing.Literal["foo"])

parse_type_tree(int)
# Unions
parse_type_tree(str | int)
parse_type_tree(typing.Union[str, int])
parse_type_tree(typing.Optional[str])
# Generics
parse_type_tree(dict[str, int])
parse_type_tree(typing.Dict[str, int])
# Other special forms
parse_type_tree(typing.Any)
parse_type_tree(typing.Literal["foo"])
