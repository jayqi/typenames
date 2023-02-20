import collections
import sys
import typing

import pytest

from typenames import (
    TypenamesConfig,
    is_standard_collection_type_alias,
    is_typing_module_collection_alias,
    is_union_or_operator,
    is_union_special_form,
    parse_type_tree,
    typenames,
)


class MyClass:
    pass


class OuterClass:
    class InnerClass:
        pass


class MyGeneric(typing.Generic[typing.T]):
    def __init__(self, x: typing.T):
        self.x = x


cases = [
    (int, "int"),
    (typing.List[int], "List[int]"),
    (typing.Tuple[str, int], "Tuple[str, int]"),
    (typing.Optional[int], "Optional[int]"),
    (MyClass, "MyClass"),
    (OuterClass.InnerClass, "OuterClass.InnerClass"),
    (typing.List[MyClass], "List[MyClass]"),
    (typing.Optional[typing.List[MyClass]], "Optional[List[MyClass]]"),
    (typing.Union[float, int], "Union[float, int]"),
    (typing.Dict[str, int], "Dict[str, int]"),
    (typing.Any, "Any"),
    (typing.Dict[str, typing.Any], "Dict[str, Any]"),
    (typing.Callable[..., str], "Callable[..., str]"),
    (typing.Callable[[int], str], "Callable[[int], str]"),
    (typing.Callable[[int, float], str], "Callable[[int, float], str]"),
    (MyGeneric[int], "MyGeneric[int]"),
    (typing.ForwardRef("MyClass"), "MyClass"),
]

if sys.version_info >= (3, 8):
    # Python 3.8 adds typing.Literal, typing.Final, typing.TypedDict

    class MyTypedDict(typing.TypedDict):
        x: int
        y: int
        label: str

    cases.extend(
        [
            (typing.Literal["r", "w"], "Literal['r', 'w']"),
            (typing.Final[int], "Final[int]"),
            (MyTypedDict, "MyTypedDict"),
        ]
    )

if sys.version_info >= (3, 9):
    # Python 3.9 adds use of standard collection types as a generic in type annotations (PEP 585),
    # typing.Annotated
    cases.extend(
        [
            (list[int], "list[int]"),
            (list[tuple[int, str]], "list[tuple[int, str]]"),
            (list[typing.Tuple[int, str]], "list[Tuple[int, str]]"),
            (
                list[collections.defaultdict[str, list[int]]],
                "list[defaultdict[str, list[int]]]",
            ),
            (collections.abc.Mapping[str, str], "Mapping[str, str]"),
        ]
    )

if sys.version_info >= (3, 10):
    # Python 3.10 adds union syntax with the | operator (bitwise or),
    # typing.Concatenate, typing.ParamSpec, typing.TypeAlias
    cases.extend(
        [
            (int | str, "int | str"),
            (int | None, "int | None"),
            (None | int, "None | int"),
        ]
    )

if sys.version_info >= (3, 11):
    # Python 3.11 adds typing.LiteralString, typing.Never, typing.Self
    pass


@pytest.mark.parametrize("case", cases, ids=[c[1] for c in cases])
def test_typenames(case):
    assert typenames(case[0]) == case[1]


def test_remove_modules():
    def remove_modules(s: str):
        config = TypenamesConfig()
        for pattern in config.remove_modules_patterns:
            s = pattern.sub("", s)
        return s

    assert remove_modules("typing.List[int]") == "List[int]"
    assert remove_modules("typing.Any") == "Any"
    assert remove_modules("collections.defaultdict") == "defaultdict"
    assert remove_modules("collections.abc.Container") == "Container"
    assert remove_modules("someothermodule.Container") == "someothermodule.Container"
    assert remove_modules("typing_other.Container") == "typing_other.Container"


def test_union_syntax_or_operator():
    """Test that forcing optional_syntax='or_operator' results in ... | ...."""
    assert typenames(typing.Union[int, str], union_syntax="or_operator") == "int | str"

    if sys.version_info >= (3, 10):
        assert typenames(int | str, union_syntax="or_operator") == "int | str"


def test_union_syntax_union_special_form():
    """Test that forcing optional_syntax='union_special_form' results in Union[...]"""
    assert (
        typenames(typing.Union[int, str], union_syntax="union_special_form") == "Union[int, str]"
    )

    if sys.version_info >= (3, 10):
        assert typenames(int | str, union_syntax="union_special_form") == "Union[int, str]"


def test_optional_syntax_or_operator():
    """Test that forcing optional_syntax='or_operator' results in ... | None."""
    assert typenames(typing.Optional[int], optional_syntax="or_operator") == "int | None"

    if sys.version_info >= (3, 10):
        assert typenames(int | None, union_syntax="or_operator") == "int | None"
        assert typenames(None | int, union_syntax="or_operator") == "None | int"


def test_optional_syntax_optional_alias():
    """Test that forcing optional_syntax='optional_special_form' results in Optional[...]."""
    assert (
        typenames(typing.Optional[int], optional_syntax="optional_special_form") == "Optional[int]"
    )

    if sys.version_info >= (3, 10):
        assert typenames(int | None, optional_syntax="optional_special_form") == "Optional[int]"
        assert typenames(None | int, optional_syntax="optional_special_form") == "Optional[int]"


def test_standard_collection_syntax_standard_class():
    """Test that forcing standard_collection_syntax='standard_class' results in standard class
    output."""
    assert typenames(typing.List[int], standard_collection_syntax="standard_class") == "list[int]"

    if sys.version_info >= (3, 9):
        assert typenames(list[int], standard_collection_syntax="standard_class") == "list[int]"


def test_standard_collection_syntax_typing_module():
    """Test that forcing standard_collection_syntax='typing_module' results in typing module
    generic aliases."""
    assert typenames(typing.List[int], standard_collection_syntax="typing_module") == "List[int]"

    if sys.version_info >= (3, 9):
        assert typenames(list[int], standard_collection_syntax="typing_module") == "List[int]"


def test_node_repr():
    assert repr(parse_type_tree(int)) == "<TypeNode <class 'int'>>"
    assert repr(parse_type_tree(typing.Any)) == "<TypeNode typing.Any>"
    assert (
        repr(parse_type_tree(typing.Optional[int]))
        == "<GenericNode typing.Union[<TypeNode <class 'int'>>, <TypeNode <class 'NoneType'>>]>"
    )

    if sys.version_info >= (3, 8):
        assert (
            repr(parse_type_tree(typing.Literal["a", "b"]))
            == "<GenericNode typing.Literal[<LiteralNode 'a'>, <LiteralNode 'b'>]>"
        )


is_union_special_form_cases = [
    (typing.Union[int, str], True),
    (typing.Optional[int], True),
    (typing.Union[typing.List[int], typing.Tuple[str, float]], True),
    (typing.Union[typing.Union[int, str], float], True),
    (typing.List[int], False),
    (typing.List[typing.Union[int, str]], False),
    (str, False),
    (type("Union", (), {}), False),
]


@pytest.mark.parametrize(
    "case", is_union_special_form_cases, ids=[str(c[0]) for c in is_union_special_form_cases]
)
def test_is_union_special_form(case):
    """Test that is_union_special_form correctly identifies if using typing.Union."""
    assert is_union_special_form(case[0]) == case[1]


@pytest.mark.parametrize(
    "case", is_union_special_form_cases, ids=[str(c[0]) for c in is_union_special_form_cases]
)
def test_is_union_or_operator_for_typing_alias_cases(case):
    """Test that is_union_or_operator correctly returns False for all typing.Union test cases."""
    assert is_union_or_operator(case[0]) is False


if sys.version_info >= (3, 10):
    # Python 3.10 adds | operator (bitwise or) for Union
    is_union_or_operator_cases = [
        (int | str, True),
        (int | None, True),
        (None | int, True),
        (int | str | float, True),
        (list[int] | tuple[str, float], True),
        (list[int | str], False),
    ]

    @pytest.mark.parametrize(
        "case", is_union_or_operator_cases, ids=[str(c[0]) for c in is_union_or_operator_cases]
    )
    def test_is_union_or_operator(case):
        """Test that is_union_or_operator correctly identifies cases using | operator."""
        assert is_union_or_operator(case[0]) == case[1]

    @pytest.mark.parametrize(
        "case", is_union_or_operator_cases, ids=[str(c[0]) for c in is_union_or_operator_cases]
    )
    def test_is_union_special_form_for_or_operator_cases(case):
        """Test that is_union_special_form correctly returns False for all | operator cases."""
        assert is_union_special_form(case[0]) is False


is_typing_module_collection_alias_cases = [
    (typing.List[int], True),
    (typing.Dict[str, int], True),
    (typing.Tuple[int, int], True),
    (typing.List[typing.Optional[int]], True),
    (typing.Dict[typing.Tuple[int, int], str], True),
    (int, False),
    (str, False),
    (typing.Optional[typing.List[int]], False),
    (typing.Union[typing.List[int], typing.List[str]], False),
    (collections.namedtuple("Point", ["x", "y"]), False),
]


@pytest.mark.parametrize(
    "case",
    is_typing_module_collection_alias_cases,
    ids=[str(c[0]) for c in is_typing_module_collection_alias_cases],
)
def test_is_typing_module_collection_alias(case):
    assert is_typing_module_collection_alias(case[0]) == case[1]


@pytest.mark.parametrize(
    "case",
    is_typing_module_collection_alias_cases,
    ids=[str(c[0]) for c in is_typing_module_collection_alias_cases],
)
def test_is_standard_collection_type_alias_for_typing_alias_cases(case):
    """Test that is_standard_collection_type_alias correctly returns False for all typing module
    alias cases."""
    assert is_standard_collection_type_alias(case[0]) is False


if sys.version_info >= (3, 9):
    # Python 3.9 adds generic aliases for standard collections
    is_standard_collection_type_alias_cases = [
        (list[int], True),
        (dict[str, int], True),
        (tuple[int, int], True),
        (list[typing.Optional[int]], True),
        (dict[tuple[int, int], str], True),
        (dict[typing.Tuple[int, int], str], True),
        (typing.Optional[list[int]], False),
        (typing.Union[list[int], list[str]], False),
    ]

    @pytest.mark.parametrize(
        "case",
        is_standard_collection_type_alias_cases,
        ids=[str(c[0]) for c in is_standard_collection_type_alias_cases],
    )
    def test_is_standard_collection_type_alias(case):
        assert is_standard_collection_type_alias(case[0]) == case[1]

    @pytest.mark.parametrize(
        "case",
        is_standard_collection_type_alias_cases,
        ids=[str(c[0]) for c in is_standard_collection_type_alias_cases],
    )
    def test_is_typing_module_collection_alias_for_collection_types(case):
        """Test that is_typing_module_collection_alias correctly returns False for all standard
        collection type aliases."""
        assert is_typing_module_collection_alias(case[0]) is False

    def test_nested_collection_types_nested_both():
        """Test that is_typing_module_collection_alias and is_standard_collection_type_alias
        correctly identify nested cases using both typing approaches."""
        tp1 = typing.Dict[tuple[int, int], str]
        assert is_typing_module_collection_alias(tp1) is True
        assert is_standard_collection_type_alias(tp1) is False

        tp2 = dict[typing.Tuple[int, int], str]
        assert is_typing_module_collection_alias(tp2) is False
        assert is_standard_collection_type_alias(tp2) is True
