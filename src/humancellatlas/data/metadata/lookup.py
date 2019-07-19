from typing import TypeVar, Mapping, Union, Iterable, List, Optional
from enum import Enum

from ingest.template.schema_template import SchemaTemplate

K = TypeVar('K')
V = TypeVar('V')

schema_template = SchemaTemplate()

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

def resolve_local_property(doc, property, context, version, default: Union[V, LookupDefault] = LookupDefault.RAISE):
    """
    use this to resolve a property name given a context and a schema version
    :param property: a single property from a schema e.g. "title"
    :param context: the fully qualified context e.g. 'project.publications.title'
    :param version: the schema version that you trying to resolve to
    :return: 
    """

    fq_key = context + "." + property
    new_k = schema_template.replaced_by_at(fq_key, version)
    property = new_k.split(".")[-1]
    try:
        return _get_path(doc, property)
    except KeyError:
        if default is LookupDefault.RAISE:
            raise
        else:
            return default

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

def get_document_version(metadata_json):
    if 'schema_version' in metadata_json:
        return metadata_json['schema_version']
    return metadata_json['describedBy'].split("/")[-2]


def lookup(d: Mapping[K, V], k: K, *ks: Iterable[K], default: Union[V, LookupDefault] = LookupDefault.RAISE) -> V:
    """
    Look up a value in the specified dictionary given one or more candidate keys.

    This function raises a key error for the first (!) key if none of the keys are present and the `default` keyword
    argument absent. If the `default` keyword argument is present (None is a valid default), this function returns
    that argument instead of raising an KeyError in that case. This is notably different to dict.get() whose default
    default is `None`. This function does not have a default default.

    :param d: a dict
    :param k: a fully qualified key to lookup in the dict eg. 'publications.title'
    :param ks: optional additional fully qualified key(s) to try if the first key is not found
    :param default: a value to return if no key is found in the dict
    :return: the value that was found in dict d, or if not found either the default is returned or a KeyError is raised

    If the first key is present, return its value ...
    >>> lookup({'a': 'b'}, 'schema.a')
    'b'

    ... and ignore the other keys.
    >>> lookup({'a': 'b'}, 'schema.a', 'schema.X')
    'b'

    If the first key is absent, try the fallbacks.
    >>> lookup({'a': 'b'}, 'schema.X', 'schema.a')
    'b'

    If the key isn't present, raise a KeyError referring to that key.
    >>> lookup({'a': 'b'}, 'schema.X')
    Traceback (most recent call last):
    ...
    KeyError: 'X'

    If neither the first key nor the fallbacks are present, raise a KeyError referring to the first key.
    >>> lookup({'a': 'b'}, 'schema.X', 'schema.Y')
    Traceback (most recent call last):
    ...
    KeyError: 'X'

    If the key isn't present but a default was passed, return the default.
    >>> lookup({'a': 'b'}, 'schema.X', default='c')
    'c'

    None is a valid default.
    >>> lookup({'a': 'b'}, 'schema.X', default=None) is None
    True
    """

    if 'schema_version' in d or 'describedBy' in d:
        version = get_document_version(d)
        new_k = schema_template.replaced_by_at(k, version)
    else:
        version = '0.0.0'
        new_k = k

    # HACK for missing entries in https://schema.dev.data.humancellatlas.org/property_migrations
    split_version = [int(x) for x in version.split('.')]
    if new_k == 'donor_organism.biological_sex' and split_version >= [10, 0, 0]:
        new_k = 'donor_organism.sex'
    if new_k == 'donor_organism.disease' and split_version >= [10, 1, 0]:
        new_k = 'donor_organism.diseases'
    if new_k == 'specimen_from_organism.disease' and split_version >= [6, 3, 0]:
        new_k = 'specimen_from_organism.diseases'
    if new_k == 'project.project_core.project_shortname' and split_version >= [7, 0, 0]:
        new_k = 'project.project_core.project_short_name'

    if (new_k != k):
        print('Warn: ' +k+ ' was migrated to ' + new_k )

    k = new_k.split('.', 1)[1] # remove the schema name

    try:
        return _get_path(d, k)
    except KeyError:
        for k in ks:
            try:
                k = k.split('.', 1)[1]
                return _get_path(d, k)
            except KeyError:
                pass
        else:
            if default is LookupDefault.RAISE:
                raise
            else:
                return default


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
    >>> ontology_label(None) is None
    True
    """
    if ontology is None:
        return None
    if isinstance(ontology, str):
        return ontology
    for field in ['ontology_label', 'text', 'ontology']:
        if field in ontology:
            return ontology.get(field)
    raise AttributeError('ontology label not found')

def get_schema_name(d):
    schema = _get_path(d, "describedBy")
    return schema.split("/")[-1]
