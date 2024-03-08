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
    """Enum for union syntax options. See "Union Syntax" section of README for documentation."""

    AS_GIVEN = "as_given"
    OR_OPERATOR = "or_operator"
    SPECIAL_FORM = "special_form"


class OptionalSyntax(str, Enum):
    """Enum for optional syntax options. See "Optional Syntax" section of README for
    documentation."""

    AS_GIVEN = "as_given"
    OR_OPERATOR = "or_operator"
    OPTIONAL_SPECIAL_FORM = "optional_special_form"
    UNION_SPECIAL_FORM = "union_special_form"


class StandardCollectionSyntax(str, Enum):
    """Enum for standard collection parameterized generic options. See "Standard Collection Syntax"
    section of README for documentation."""

    AS_GIVEN = "as_given"
    STANDARD_CLASS = "standard_class"
    TYPING_MODULE = "typing_module"


DEFAULT_REMOVE_MODULES: List[Union[str, re.Pattern]] = [
    "__main__",
    "builtins",
    re.compile(r"^collections\.(abc\.)?"),
    "contextlib",
    "re",
    "types",
    "typing",
]
"""List of standard library modules used as the default value for the remove_modules option."""

REMOVE_ALL_MODULES = [re.compile(r"^(<?\w+>?\.)+")]


@dataclasses.dataclass
class TypenamesConfig:
    """Dataclass that holds all configuration options. See "Configurable options" section of README
    for documentation."""

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
        """Generator that yields remove_modules configuration values as compiled regex
        patterns."""
        for module in self.remove_modules:
            if isinstance(module, re.Pattern):
                yield module
            else:
                yield re.compile(r"^{}\.".format(module.replace(".", r"\.")))


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

    def process_module_prefix(self, module_prefix: str) -> str:
        """Processes a module prefix (including the trailing '.') according to the 'remove_modules'
        settings in the given configuration."""
        # Remove module names
        for pattern in self.config.remove_modules_patterns:
            module_prefix = pattern.sub("", module_prefix)
        return module_prefix

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {repr(self.tp)}>"


@dataclasses.dataclass(repr=False)
class TypeNode(BaseNode):
    """Node that represents a singleton type."""

    @property
    def is_none_type(self) -> bool:
        return self.tp is type(None)

    def __str__(self) -> str:
        if hasattr(self.tp, "__module__"):
            module_prefix = getattr(self.tp, "__module__") + "."
        else:
            module_prefix = ""

        if self.tp is Ellipsis:
            type_name = "..."
        elif self.tp is type(None):
            type_name = "None"
        elif self.tp is typing.Any:
            type_name = "Any"
        elif isinstance(self.tp, typing.ForwardRef):
            forward_arg = self.tp.__forward_arg__
            # Assume if there is dotted path, then it is a module path
            if "." in forward_arg:
                module, dot, type_name = forward_arg.rpartition(".")
                module_prefix = module + dot
            else:
                type_name = forward_arg
        else:
            type_name = getattr(self.tp, "__qualname__", repr(self.tp))
        for pattern in self.config.remove_modules_patterns:
            type_name = pattern.sub("", type_name)
        # Remove module names
        module_prefix = self.process_module_prefix(module_prefix)

        return module_prefix + type_name


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
                elif self.config.optional_syntax == OptionalSyntax.UNION_SPECIAL_FORM:
                    origin_module_prefix = "typing."
                    origin_name = "Union"
                else:
                    origin_module_prefix = "typing."
                    origin_name = "Optional"
                    arg_nodes = [a for a in arg_nodes if a.tp is not type(None)]
                    if len(arg_nodes) > 1:
                        # typing.Optional is only valid for a single parameter,
                        # need to use a union inside
                        arg_nodes = [
                            GenericNode(
                                tp=typing.Union[  # type: ignore[arg-type]
                                    tuple(a.tp for a in arg_nodes)
                                ],
                                config=self.config,
                                origin=typing.Union,
                                arg_nodes=arg_nodes,
                            )
                        ]

            # Case: regular Union
            else:
                if self.config.union_syntax == UnionSyntax.OR_OPERATOR:
                    return " | ".join(str(a) for a in arg_nodes)
                else:
                    origin_module_prefix = "typing."
                    origin_name = "Union"
        # Case: Union with | operator (bitwise or)
        elif is_union_or_operator(self.tp):
            is_optional = any(a.is_none_type for a in arg_nodes)
            # Case: ... | None (optional) and configured to use typing.Optional
            if is_optional and self.config.optional_syntax == OptionalSyntax.OPTIONAL_SPECIAL_FORM:
                origin_module_prefix = "typing."
                origin_name = "Optional"
                arg_nodes = [a for a in arg_nodes if a.tp is not type(None)]
                if len(arg_nodes) > 1:
                    # typing.Optional is only valid for a single parameter,
                    # need to use a union inside
                    arg_nodes = [
                        GenericNode(
                            tp=typing.Union[  # type: ignore[arg-type]
                                tuple(a.tp for a in arg_nodes)
                            ],
                            config=self.config,
                            origin=typing.Union,
                            arg_nodes=arg_nodes,
                        )
                    ]
            # Case: ... | None (optional) and configured to use typing.Union
            elif is_optional and self.config.optional_syntax == OptionalSyntax.UNION_SPECIAL_FORM:
                origin_module_prefix = "typing."
                origin_name = "Union"
            # Case: regular union
            else:
                if self.config.union_syntax == UnionSyntax.SPECIAL_FORM:
                    origin_module_prefix = "typing."
                    origin_name = "Union"
                else:
                    return " | ".join(str(a) for a in arg_nodes)
        # Case: Standard collection class alias
        elif is_standard_collection_type_alias(self.tp):
            if self.config.standard_collection_syntax == StandardCollectionSyntax.TYPING_MODULE:
                typing_alias = STANDARD_COLLECTION_TO_TYPING_ALIAS_MAPPING[
                    get_origin(self.tp)  # type: ignore
                ]
                origin_module_prefix = "typing."
                origin_name = f"{typing_alias._name}"  # type: ignore
            else:
                origin_module_prefix = self.origin.__module__ + "."
                origin_name = self.origin.__qualname__  # type: ignore[union-attr]
        # Case: Typing module collection alias
        elif is_typing_module_collection_alias(self.tp):
            if self.config.standard_collection_syntax == StandardCollectionSyntax.STANDARD_CLASS:
                origin_module_prefix = self.origin.__module__ + "."
                origin_name = self.origin.__qualname__  # type: ignore[union-attr]
            else:
                origin_module_prefix = "typing."
                origin_name = self.tp._name
        # Case: Some other generic type
        else:
            if hasattr(self.origin, "__module__"):
                origin_module_prefix = self.origin.__module__ + "."
            else:
                origin_module_prefix = ""
            origin_name = getattr(
                self.origin, "__name__", getattr(self.origin, "_name", str(self.origin))
            )

        # Remove module names
        origin_module_prefix = self.process_module_prefix(origin_module_prefix)

        args_string = ", ".join(str(a) for a in arg_nodes)
        return f"{origin_module_prefix}{origin_name}[{args_string}]"

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
        if isinstance(self.tp, Enum):
            return f"{self.tp.__class__.__name__}.{self.tp.name}"
        else:
            return repr(self.tp)


def parse_type_tree(tp: type, config: Optional[TypenamesConfig] = None, **kwargs: Any) -> BaseNode:
    """Parses a given type annotation into a tree data structure.

    Args:
        tp (type): Type annotation
        config (Optional[TypenamesConfig]): Configuration dataclass. Defaults to None, which will
            instantiate one with default values.
        **kwargs: Override configuration options on provided or default configuration. See
            "Configurable options" section of README for documentation.

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
        **kwargs: Override configuration options on provided or default configuration. See
            "Configurable options" section of README for documentation.

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
