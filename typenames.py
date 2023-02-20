import abc
import collections
import contextlib
import dataclasses
from enum import Enum
import re
import sys
import types
import typing
from typing import Any, List, Optional, Union

try:
    from typing import get_args, get_origin  # type: ignore # Python 3.8+
except ImportError:
    from typing_extensions import get_args, get_origin  # type: ignore # Python 3.7


__version__ = "1.0.0"

OR_OPERATOR_SUPPORTED = sys.version_info >= (3, 10)
"""Flag for whether PEP 604's | operator (bitwise or) between types is supported."""

LITERAL_TYPE_SUPPORTED = sys.version_info >= (3, 8)
"""Flag for whether PEP 586's typing.Literal is supported."""


T = typing.TypeVar("T", bound=type)


class UnionSyntax(str, Enum):
    AS_GIVEN = "as_given"
    OR_OPERATOR = "or_operator"
    UNION_SPECIAL_FORM = "union_special_form"


class OptionalSyntax(str, Enum):
    AS_GIVEN = "as_given"
    OR_OPERATOR = "or_operator"
    OPTIONAL_SPECIAL_FORM = "optional_special_form"


class StandardCollectionSyntax(str, Enum):
    AS_GIVEN = "as_given"
    STANDARD_CLASS = "standard_class"
    TYPING_MODULE = "typing_module"


DEFAULT_REMOVE_MODULES: typing.List[typing.Union[str, re.Pattern]] = [
    "builtins",
    "typing",
    re.compile(r"^collections\.(abc\.)?"),
    "contextlib",
    "re",
]
"""List of standard library modules used as the default value for the remove_modules option. """


@dataclasses.dataclass
class TypenamesConfig:
    union_syntax: UnionSyntax = UnionSyntax.AS_GIVEN
    optional_syntax: OptionalSyntax = OptionalSyntax.AS_GIVEN
    standard_collection_syntax: StandardCollectionSyntax = StandardCollectionSyntax.AS_GIVEN
    remove_modules: List[Union[str, re.Pattern]] = dataclasses.field(
        default_factory=lambda: list(DEFAULT_REMOVE_MODULES)
    )

    def __post_init__(self):
        self.union_syntax = UnionSyntax(self.union_syntax)
        self.optional_syntax = OptionalSyntax(self.optional_syntax)
        self.standard_collection_syntax = StandardCollectionSyntax(self.standard_collection_syntax)

    @property
    def remove_modules_patterns(self) -> typing.Iterator[re.Pattern]:
        """Generator that returns remove_modules configuration values as compiled regex
        patterns."""
        for m in self.remove_modules:
            if isinstance(m, re.Pattern):
                yield m
            yield re.compile(rf"^{m}\.")


@dataclasses.dataclass(repr=False)
class BaseNode(abc.ABC, typing.Generic[T]):
    """Abstract base class for a typenames node."""

    tp: typing.Type[T]
    config: TypenamesConfig

    @property
    @abc.abstractmethod
    def is_none_type(self) -> bool:
        """Whether this node corresponds to NoneType, which is the type of None. Used to identify
        the "Optional" special case of a union of types.

        Returns:
            bool: True if this node's tp is NoneType.
        """

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {repr(self.tp)}>"


@dataclasses.dataclass(repr=False)
class TypeNode(BaseNode):
    """Node that represents a singleton type."""

    @property
    def is_none_type(self) -> bool:
        return self.tp is type(None)

    def __str__(self) -> str:
        if self.tp is Ellipsis:
            type_name = "..."
        elif self.tp is type(None):
            type_name = "None"
        elif isinstance(self.tp, typing.ForwardRef):
            type_name = self.tp.__forward_arg__
        else:
            type_name = getattr(self.tp, "__qualname__", repr(self.tp))
        for pattern in self.config.remove_modules_patterns:
            type_name = pattern.sub("", type_name)
        return type_name


@dataclasses.dataclass(repr=False)
class GenericNode(BaseNode):
    """Node that represents a generic type."""

    origin: Union[Any, None]
    arg_nodes: List[BaseNode]

    @property
    def is_none_type(self) -> bool:
        return False

    def __str__(self) -> str:
        arg_nodes = list(self.arg_nodes)

        # Case: typing.Union
        if is_union_special_form(self.tp):
            # Case: typing.Optional
            if any(a.is_none_type for a in arg_nodes):
                if self.config.optional_syntax == OptionalSyntax.OR_OPERATOR:
                    return " | ".join(str(a) for a in arg_nodes)
                else:
                    origin_name = "typing.Optional"
                    arg_nodes = [a for a in arg_nodes if a.tp is not type(None)]
            # Case: regular Union
            else:
                if self.config.union_syntax == UnionSyntax.OR_OPERATOR:
                    return " | ".join(str(a) for a in arg_nodes)
                else:
                    origin_name = "typing.Union"
        # Case: Union with | operator (bitwise or)
        elif is_union_or_operator(self.tp):
            # Case: ... | None and configured to use typing.Optional
            if self.config.optional_syntax == OptionalSyntax.OPTIONAL_SPECIAL_FORM and any(
                a.is_none_type for a in arg_nodes
            ):
                origin_name = "typing.Optional"
                arg_nodes = [a for a in arg_nodes if a.tp is not type(None)]
            # Case: regular union
            else:
                if self.config.union_syntax == UnionSyntax.UNION_SPECIAL_FORM:
                    origin_name = "typing.Union"
                else:
                    return " | ".join(str(a) for a in arg_nodes)
        # Case: Standard collection class alias
        elif is_standard_collection_type_alias(self.tp):
            if self.config.standard_collection_syntax == StandardCollectionSyntax.TYPING_MODULE:
                typing_alias = STANDARD_COLLECTION_TO_TYPING_ALIAS_MAPPING[
                    get_origin(self.tp)  # type: ignore
                ]
                origin_name = f"typing.{typing_alias._name}"  # type: ignore
            else:
                origin_name = (
                    self.origin.__module__
                    + "."
                    + self.origin.__qualname__  # type: ignore[union-attr]
                )
        # Case: Typing module collection alias
        elif is_typing_module_collection_alias(self.tp):
            if self.config.standard_collection_syntax == StandardCollectionSyntax.STANDARD_CLASS:
                origin_name = (
                    self.origin.__module__
                    + "."
                    + self.origin.__qualname__  # type: ignore[union-attr]
                )
            else:
                origin_name = f"typing.{self.tp._name}"
        # Case: Some other generic type
        else:
            origin_name = getattr(self.origin, "__name__", str(self.origin))

        # Remove module names
        for pattern in self.config.remove_modules_patterns:
            origin_name = pattern.sub("", origin_name)

        args_string = ", ".join(str(a) for a in arg_nodes)
        return f"{origin_name}[{args_string}]"

    def __repr__(self) -> str:
        args_repr = ", ".join(repr(a) for a in self.arg_nodes)
        return f"<{type(self).__name__} {repr(self.origin)}[{args_repr}]>"


@dataclasses.dataclass(repr=False)
class ParamsListNode(BaseNode):
    """Node that represents a list of parameters. Used for the arguments of Callable."""

    arg_nodes: List[BaseNode]

    @property
    def is_none_type(self) -> typing.NoReturn:
        # Don't expect to call this—only used for checking args of union
        raise NotImplementedError(  # pragma: no cover
            "ParamsListNode.is_none_type should not be called."
        )

    def __str__(self) -> str:
        args_string = ", ".join(str(a) for a in self.arg_nodes)
        return f"[{args_string}]"


@dataclasses.dataclass(repr=False)
class LiteralNode(BaseNode):
    """Node that represents a literal value. Used for the arguments of Literal. Valid types for
    a literal value include ints, byte strings, unicode strings, bools, Enum values, None."""

    @property
    def is_none_type(self) -> typing.NoReturn:
        # Don't expect to call this—only used for checking args of union
        raise NotImplementedError(  # pragma: no cover
            "LiteralNode.is_none_type should not be called."
        )

    def __str__(self) -> str:
        return repr(self.tp)


def parse_type_tree(tp: type, config: Optional[TypenamesConfig] = None, **kwargs: Any) -> BaseNode:
    """Parses a given type annotation into a tree data structure.

    Args:
        tp (type): Type annotation
        config (Optional[TypenamesConfig]): Configuration dataclass. Defaults to None, which will
            instantiate one with default values.
        **kwargs: Override configuration options on provided or default configuration.

    Returns:
        BaseNode: Root node of parsed type tree
    """
    if config is None:
        config = TypenamesConfig(**kwargs)
    else:
        config = dataclasses.replace(config, **kwargs)

    node: BaseNode
    origin = get_origin(tp)
    if origin:
        args = get_args(tp)
        node = GenericNode(
            tp=tp,
            origin=origin,
            arg_nodes=[parse_type_tree(a, config=config) for a in args],
            config=config,
        )
    elif isinstance(tp, list):
        # This is the parameter list for Callable
        node = ParamsListNode(tp=tp, arg_nodes=[parse_type_tree(a) for a in tp], config=config)
    elif isinstance(tp, (int, bytes, str, Enum, bool)) or tp is None:
        node = LiteralNode(tp=tp, config=config)
    else:
        node = TypeNode(tp=tp, config=config)
    return node


def typenames(tp: type, config: Optional[TypenamesConfig] = None, **kwargs: Any) -> str:
    """Render a string representation of a type annotation.

    Args:
        tp (type): Type annotation.
        config (Optional[TypenamesConfig]): Configuration dataclass. Defaults to None, which will
            instantiate one with default values.
        **kwargs: Override configuration options on provided or default configuration.

    Returns:
        str: String representation of input type.
    """
    tree = parse_type_tree(tp=tp, config=config, **kwargs)
    return str(tree)


def is_union_special_form(tp: type) -> bool:
    """Check if type annotation is a union and uses the typing.Union special form."""
    return get_origin(tp) is typing.Union


def is_union_or_operator(tp: type) -> bool:
    """Check if type annotation is a union and uses | operator (bitwise or)."""
    return OR_OPERATOR_SUPPORTED and isinstance(tp, types.UnionType)


STANDARD_COLLECTION_TO_TYPING_ALIAS_MAPPING: typing.Dict[  # type: ignore[name-defined]
    type, typing._GenericAlias
] = {
    # builtins module
    dict: typing.Dict,
    list: typing.List,
    set: typing.Set,
    frozenset: typing.FrozenSet,
    tuple: typing.Tuple,
    # collections module
    collections.defaultdict: typing.DefaultDict,
    collections.OrderedDict: typing.OrderedDict,
    collections.ChainMap: typing.ChainMap,
    collections.Counter: typing.Counter,
    collections.deque: typing.Deque,
    # collections.abc module
    collections.abc.Awaitable: typing.Awaitable,
    collections.abc.Coroutine: typing.Coroutine,
    collections.abc.AsyncIterable: typing.AsyncIterable,
    collections.abc.AsyncIterator: typing.AsyncIterator,
    collections.abc.AsyncGenerator: typing.AsyncGenerator,
    collections.abc.Iterable: typing.Iterable,
    collections.abc.Iterator: typing.Iterator,
    collections.abc.Generator: typing.Generator,
    collections.abc.Reversible: typing.Reversible,
    collections.abc.Collection: typing.Collection,
    collections.abc.Container: typing.Container,
    collections.abc.Callable: typing.Callable,  # type: ignore[dict-item]
    collections.abc.Set: typing.AbstractSet,
    collections.abc.MutableSet: typing.MutableSet,
    collections.abc.Mapping: typing.Mapping,
    collections.abc.MutableMapping: typing.MutableMapping,
    collections.abc.Sequence: typing.Sequence,
    collections.abc.MutableSequence: typing.MutableSequence,
    collections.abc.ByteString: typing.ByteString,
    collections.abc.MappingView: typing.MappingView,
    collections.abc.KeysView: typing.KeysView,
    collections.abc.ItemsView: typing.ItemsView,
    collections.abc.ValuesView: typing.ValuesView,
    # contextlib module
    contextlib.AbstractContextManager: typing.ContextManager,
    contextlib.AbstractAsyncContextManager: typing.AsyncContextManager,
    # re module
    re.Pattern: typing.Pattern,
    re.Match: typing.Match,
}
"""Mapping from standard collection types that support use as a generic type starting in
Python 3.9 (PEP 585) to their associated typing module generic alias."""

STANDARD_COLLECTION_CLASSES: typing.FrozenSet[type] = frozenset(
    STANDARD_COLLECTION_TO_TYPING_ALIAS_MAPPING.keys()
)
"""Frozenset of standard collection classes that support use as a generic type starting in
Python 3.9 (PEP 585)."""


def is_standard_collection_type_alias(tp: type) -> bool:
    """Check if type annotation is a generic type and uses a standard collection type as a generic
    alias."""
    return (
        get_origin(tp) in STANDARD_COLLECTION_CLASSES
        and type(tp) is not typing._GenericAlias  # type: ignore[attr-defined]
    )


def is_typing_module_collection_alias(tp: type) -> bool:
    """Check if type annotation is a generic type and uses a typing module collection generic
    alias, e.g., typing.List."""
    return (
        get_origin(tp) in STANDARD_COLLECTION_CLASSES
        and type(tp) is typing._GenericAlias  # type: ignore[attr-defined]
    )
