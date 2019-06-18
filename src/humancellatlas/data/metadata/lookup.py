from typing import TypeVar, Mapping, Union, Iterable, List
from enum import Enum
from jsonpath_rw import jsonpath, parse

K = TypeVar('K')
V = TypeVar('V')


class PropertyMigration:
    def __init__(self, source_schema: str, property: str, target_schema: str, replaced_by:str, effective_from: str, reason: str, type: str):
        self.source_schema = source_schema
        self.property = property
        self.target_schema = target_schema
        self.replaced_by = replaced_by
        self.effective_from  = effective_from
        self.reason = reason
        self.type = type

class LookupDefault(Enum):
    RAISE = 0

def _get_path(d: Mapping[K, V], json_path: str):
    jsonpath_expr = parse(json_path)
    return [match.value for match in jsonpath_expr.find(d)]


def lookup(d: Mapping[K, V], k: K, *ks: Iterable[K], default: Union[V, LookupDefault] = LookupDefault.RAISE) -> V:
    """
    Look up a value in the specified dictionary given one or more candidate keys.

    This function raises a key error for the first (!) key if none of the keys are present and the `default` keyword
    argument absent. If the `default` keyword argument is present (None is a valid default), this function returns
    that argument instead of raising an KeyError in that case. This is notably different to dict.get() whose default
    default is `None`. This function does not have a default default.

    If the first key is present, return its value ...
    >>> lookup({1:2}, 1)
    2

    ... and ignore the other keys.
    >>> lookup({1:2}, 1, 3)
    2

    If the first key is absent, try the fallbacks.
    >>> lookup({1:2}, 3, 1)
    2

    If the key isn't present, raise a KeyError referring to that key.
    >>> lookup({1:2}, 3)
    Traceback (most recent call last):
    ...
    KeyError: 3

    If neither the first key nor the fallbacks are present, raise a KeyError referring to the first key.
    >>> lookup({1:2}, 3, 4)
    Traceback (most recent call last):
    ...
    KeyError: 3

    If the key isn't present but a default was passed, return the default.
    >>> lookup({1:2}, 3, default=4)
    4

    None is a valid default.
    >>> lookup({1:2}, 3, 4, default=None) is None
    True
    """
    try:
        return d[k]
    except KeyError:
        for k in ks:
            try:
                return d[k]
            except KeyError:
                pass
        else:
            if default is LookupDefault.RAISE:
                raise
            else:
                return default


# def lookup2(d: Mapping[K, V], initial_key: K, property_migrations: List[PropertyMigration], default: Union[V, LookupDefault] = LookupDefault.RAISE) -> V:
#
#
