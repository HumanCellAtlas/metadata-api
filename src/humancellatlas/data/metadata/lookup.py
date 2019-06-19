from typing import TypeVar, Mapping, Union, Iterable, List, Optional
from enum import Enum

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
    """
    Get the value in the mapping for the JSON path.

    Note that {"key": ["value"]} and [{"key": "value"}] have the same path.

    :param d: The JSON object to inspect
    :param json_path: keys.separated.by.dots
    >>> _get_path({'a': {'b': {'c': 'd'}}}, 'a.b.c')
    'd'
    >>> _get_path({'a': {'b': {'c': ['d']}}}, 'a.b.c')
    ['d']
    >>> _get_path({'a': {'b': [{'c': 'd'}]}}, 'a.b.c')
    'd'
    >>> _get_path({'a': {'b': [{'c': 'd'}, {'c': 'e'}]}}, 'a.b.c')
    ['d', 'e']
    >>> _get_path({'a': {'b': [{'c': ['d']}, {'c': 'e'}]}}, 'a.b.c')
    [['d'], 'e']
    >>> _get_path({'a': [{'b': [{'c': 'd'}, {'c': 'e'}]}, {'b': {'c': 'f'}}]}, 'a.b.c')
    ['d', 'e', 'f']
    >>> _get_path({'a': {'b': {'X': 'd'}}}, 'a.b.c')
    Traceback (most recent call last):
        ...
    KeyError: 'c'
    >>> _get_path({'a': {'b': [{'c': 'd'}, {'X': 'e'}]}}, 'a.b.c')
    Traceback (most recent call last):
        ...
    KeyError: 'c'
    >>> _get_path({'a': [{'b': [{'c': 'd'}, {'c': 'e'}]}, {'b': {'X': 'f'}}]}, 'a.b.c')
    Traceback (most recent call last):
        ...
    KeyError: 'c'
    """
    matches = _recursive_get_path([d], json_path.split('.'))
    if len(matches) == 1:
        return matches[0]
    else:
        return matches


def split_path(path):
    return path[0], path[1:]


def _recursive_get_path(matching_objs: Iterable[Mapping[K, V]], unmatched_path: List[str]):
    if len(unmatched_path) == 0:
        return matching_objs
    else:
        head, tail = split_path(unmatched_path)
        matches = []
        for obj in matching_objs:
            if type(obj) == dict:
                matches.append(obj[head])
            elif type(obj) == list:
                for sub_obj in obj:
                    if type(sub_obj) == dict:
                        matches.append(sub_obj[head])
                    else:
                        raise KeyError(f'Cannot match key: {head} in object: {sub_obj} of type: {type(sub_obj)}')
            else:
                raise KeyError(f'Cannot match key: {head} in object: {obj} of type: {type(obj)}')
        assert len(matches) > 0
        return _recursive_get_path(matches, tail)


def lookup(d: Mapping[K, V], k: K, *ks: Iterable[K], default: Union[V, LookupDefault] = LookupDefault.RAISE) -> V:
    """
    Look up a value in the specified dictionary given one or more candidate keys.

    This function raises a key error for the first (!) key if none of the keys are present and the `default` keyword
    argument absent. If the `default` keyword argument is present (None is a valid default), this function returns
    that argument instead of raising an KeyError in that case. This is notably different to dict.get() whose default
    default is `None`. This function does not have a default default.

    If the first key is present, return its value ...
    >>> lookup({'a': 'b'}, 'a')
    'b'

    ... and ignore the other keys.
    >>> lookup({'a': 'b'}, 'a', 'X')
    'b'

    If the first key is absent, try the fallbacks.
    >>> lookup({'a': 'b'}, 'X', 'a')
    'b'

    If the key isn't present, raise a KeyError referring to that key.
    >>> lookup({'a': 'b'}, 'X')
    Traceback (most recent call last):
    ...
    KeyError: 'X'

    If neither the first key nor the fallbacks are present, raise a KeyError referring to the first key.
    >>> lookup({'a': 'b'}, 'X', 'Y')
    Traceback (most recent call last):
    ...
    KeyError: 'X'

    If the key isn't present but a default was passed, return the default.
    >>> lookup({'a': 'b'}, 'X', default='c')
    'c'

    None is a valid default.
    >>> lookup({'a': 'b'}, 'X', default=None) is None
    True
    """
    k = k.split('.', 1)[1]
    try:
        return _get_path(d, k)
    except KeyError:
        for k in ks:
            try:
                return _get_path(d, k)
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

def ontology_label(ontology: Optional[Mapping[str, str]]) -> str:
    """
    Return the best-suited value from the given ontology dictionary.

    If the preferred key is present, return its value ...
    >>> ontology_label({'ontology_label': 'a', 'text': 'b', 'ontology': 'c'})
    'a'

    If the preferred key is not present, return the next preferred ...
    >>> ontology_label({'text': 'b', 'ontology': 'c'})
    'b'

    If no preferred key is present, raise an AttributeError
    >>> ontology_label({'description': 'z'})
    Traceback (most recent call last):
    ...
    AttributeError: ontology label not found

    If given None, return None
    >>> ontology_label(None)
    None
    """
    if ontology is None:
        return None
    for field in ['ontology_label', 'text', 'ontology']:
        if field in ontology:
            return ontology.get(field)
    raise AttributeError('ontology label not found')

