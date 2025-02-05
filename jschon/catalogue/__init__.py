import pathlib
import uuid
from contextlib import contextmanager
from os import PathLike
from typing import Dict, Mapping, Optional, Hashable, ContextManager

from jschon.catalogue import _2019_09, _2020_12
from jschon.exceptions import CatalogueError, JSONPointerError, URIError
from jschon.json import AnyJSONCompatible
from jschon.jsonpointer import JSONPointer
from jschon.jsonschema import JSONSchema
from jschon.uri import URI
from jschon.utils import json_loadf
from jschon.vocabulary import Vocabulary, KeywordClass, Metaschema
from jschon.vocabulary.format import FormatValidator

__all__ = [
    'Catalogue',
]


class Catalogue:
    """The catalogue is the largest organizational unit in jschon.

    A :class:`Catalogue` instance is an in-memory schema cache, usually
    initialized with a metaschema and its associated vocabularies, and
    optionally with any number of format validators. It may be configured
    with base URI-to-directory mappings, to enable loading of URI-identified
    JSON and JSON schema resources from disk.
    """
    _version_initializers = {
        '2019-09': _2019_09.initialize,
        '2020-12': _2020_12.initialize,
    }
    _default_catalogue: 'Catalogue' = None

    @classmethod
    def get_default(cls) -> Optional['Catalogue']:
        """Get the default :class:`Catalogue` instance, if there is one."""
        return cls._default_catalogue

    def __init__(self, *versions: str, default: bool):
        """Initialize a :class:`Catalogue` instance.
        
        :param versions: any of ``'2019-09'``, ``'2020-12'``
        :param default: if True, new :class:`~jschon.jsonschema.JSONSchema`
            instances are by default cached in this catalogue
        :raise CatalogueError: if a supplied version parameter is not recognized
        """
        self._directories: Dict[URI, PathLike] = {}
        self._vocabularies: Dict[URI, Vocabulary] = {}
        self._format_validators: Dict[str, FormatValidator] = {}
        self._schema_cache: Dict[Hashable, Dict[URI, JSONSchema]] = {}
        try:
            initializers = [self._version_initializers[version] for version in versions]
        except KeyError as e:
            raise CatalogueError(f'Unrecognized version "{e.args[0]}"')

        for initializer in initializers:
            initializer(self)

        if default:
            Catalogue._default_catalogue = self

    def add_directory(self, base_uri: URI, base_dir: PathLike) -> None:
        """Register a base URI-to-directory mapping.
        
        This enables JSON objects identified by URIs with a given base URI
        to be loaded from files within a corresponding directory hierarchy,
        as described under :meth:`load_json`.

        :param base_uri: a normalized, absolute URI - including scheme, without
            a fragment, and ending with ``'/'``
        :param base_dir: a directory path accessible on the file system
        :raise CatalogueError: if either `base_uri` or `base_dir` is invalid
        """
        try:
            base_uri.validate(require_scheme=True, require_normalized=True, allow_fragment=False)
        except URIError as e:
            raise CatalogueError from e

        if not base_uri.path or not base_uri.path.endswith('/'):
            raise CatalogueError("base_uri must end with '/'")

        if not pathlib.Path(base_dir).is_dir():
            raise CatalogueError(f"'{base_dir}' is not a directory")

        self._directories[base_uri] = base_dir

    def load_json(self, uri: URI) -> AnyJSONCompatible:
        """Load a JSON-compatible object from the file corresponding to `uri`.
        
        The file path is determined by selecting the most specific matching
        base URI that was registered with :meth:`add_directory`, and resolving
        the remainder of `uri` against the corresponding base directory.

        :param uri: a normalized, absolute URI - including scheme, without
            a fragment
        :raise CatalogueError: if `uri` is invalid, or if a corresponding
            file cannot be found
        """
        try:
            uri.validate(require_scheme=True, require_normalized=True, allow_fragment=False)
        except URIError as e:
            raise CatalogueError from e

        uristr = str(uri)
        candidates = [
            (str(base_uri), base_dir)
            for base_uri, base_dir in self._directories.items()
            if uristr.startswith(str(base_uri))
        ]
        if candidates:
            # if there is more than one candidate base URI, we consider
            # only the longest one to be a match: it represents a mount
            # of a directory at a sub-path of a parent candidate, and
            # we shouldn't fall back to trying to find the file in the
            # parent's directory hierarchy
            candidates.sort(key=lambda c: len(c[0]), reverse=True)
            base_uristr, base_dir = candidates[0]
            filepath = pathlib.Path(base_dir) / uristr[len(base_uristr):]
            try:
                return json_loadf(filepath)
            except FileNotFoundError:
                pass
            try:
                return json_loadf(filepath.with_suffix('.json'))
            except FileNotFoundError:
                pass

        raise CatalogueError(f"File not found for '{uri}'")

    def create_vocabulary(self, uri: URI, *kwclasses: KeywordClass) -> None:
        """Create a :class:`~jschon.vocabulary.Vocabulary` object, which
        may be used by a :class:`~jschon.vocabulary.Metaschema` to provide
        keyword classes used in schema construction.

        :param uri: the URI identifying the vocabulary
        :param kwclasses: the :class:`~jschon.vocabulary.Keyword` classes
            constituting the vocabulary
        """
        self._vocabularies[uri] = Vocabulary(uri, *kwclasses)

    def get_vocabulary(self, uri: URI) -> Vocabulary:
        """Get a :class:`~jschon.vocabulary.Vocabulary` by its `uri`.

        :param uri: the URI identifying the vocabulary
        :raise CatalogueError: if `uri` is not a recognized vocabulary URI
        """
        try:
            return self._vocabularies[uri]
        except KeyError:
            raise CatalogueError(f"Unrecognized vocabulary URI '{uri}'")

    def create_metaschema(
            self,
            metaschema_uri: URI,
            core_vocabulary_uri: URI,
            *default_vocabulary_uris: URI,
    ) -> None:
        """Create, cache and validate a :class:`~jschon.vocabulary.Metaschema`.

        :param metaschema_uri: the URI identifying the metaschema
        :param core_vocabulary_uri: the URI identifying the metaschema's
            core :class:`~jschon.vocabulary.Vocabulary`
        :param default_vocabulary_uris: default :class:`~jschon.vocabulary.Vocabulary`
            URIs, used in the absence of a ``"$vocabulary"`` keyword in the
            metaschema JSON file
        """
        metaschema_doc = self.load_json(metaschema_uri)
        core_vocabulary = self.get_vocabulary(core_vocabulary_uri)
        default_vocabularies = [self.get_vocabulary(vocab_uri) for vocab_uri in default_vocabulary_uris]
        metaschema = Metaschema(self, metaschema_doc, core_vocabulary, *default_vocabularies)
        if not metaschema.validate().valid:
            raise CatalogueError("The metaschema is invalid against itself")

    def add_format_validators(self, validators: Mapping[str, FormatValidator]) -> None:
        """Register a collection of format validators.
        
        In jschon, a given occurrence of the ``"format"`` keyword evaluates
        a JSON instance using a format validation callable, if one has been
        registered for the applicable *format attribute* (the keyword's value).
        If a validator has not been registered for that format attribute,
        keyword evaluation simply passes.

        :param validators: a dictionary of :class:`~jschon.vocabulary.format.FormatValidator`
            callables, keyed by format attribute
        """
        self._format_validators.update(validators)

    def get_format_validator(self, format_attr: str) -> FormatValidator:
        """Get a registered :class:`~jschon.vocabulary.format.FormatValidator`
        function.

        :param format_attr: the format attribute (``"format"`` keyword value)
            to which the validator applies
        :raise CatalogueError: if no format validator is registered for the
            given `format_attr`
        """
        try:
            return self._format_validators[format_attr]
        except KeyError:
            raise CatalogueError(f"Unsupported format attribute '{format_attr}'")

    def add_schema(
            self,
            uri: URI,
            schema: JSONSchema,
            *,
            session: Hashable = 'default',
    ) -> None:
        """Add a (sub)schema to a session cache.

        :param uri: the URI identifying the (sub)schema
        :param schema: the :class:`~jschon.jsonschema.JSONSchema` instance to cache
        :param session: a session identifier
        """
        self._schema_cache.setdefault(session, {})
        self._schema_cache[session][uri] = schema

    def del_schema(
            self,
            uri: URI,
            *,
            session: Hashable = 'default',
    ) -> None:
        """Remove a (sub)schema from a session cache.

        :param uri: the URI identifying the (sub)schema
        :param session: a session identifier
        """
        if session in self._schema_cache:
            self._schema_cache[session].pop(uri, None)

    def get_schema(
            self,
            uri: URI,
            *,
            metaschema_uri: URI = None,
            session: Hashable = 'default',
    ) -> JSONSchema:
        """Get a (sub)schema identified by `uri` from the session cache, or
        load it from disk if not already cached.

        :param uri: the URI identifying the (sub)schema
        :param metaschema_uri: passed to the :class:`~jschon.jsonschema.JSONSchema`
            constructor when loading a new instance from disk
        :param session: a session identifier
        :raise CatalogueError: if a schema cannot be found for `uri`, or if the
            object referenced by `uri` is not a :class:`~jschon.jsonschema.JSONSchema`
        """
        try_caches = ('__meta__',) \
            if session == '__meta__' \
            else (session, '__meta__')

        for cacheid in try_caches:
            try:
                return self._schema_cache[cacheid][uri]
            except KeyError:
                pass

        schema = None
        base_uri = uri.copy(fragment=False)

        if uri.fragment is not None:
            for cacheid in try_caches:
                try:
                    schema = self._schema_cache[cacheid][base_uri]
                    break
                except KeyError:
                    pass

        if schema is None:
            doc = self.load_json(base_uri)
            schema = JSONSchema(
                doc,
                catalogue=self,
                session=session,
                uri=base_uri,
                metaschema_uri=metaschema_uri,
            )

        if uri.fragment:
            try:
                ptr = JSONPointer.parse_uri_fragment(uri.fragment)
                schema = ptr.evaluate(schema)
            except JSONPointerError as e:
                raise CatalogueError(f"Schema not found for {uri}") from e

        if not isinstance(schema, JSONSchema):
            raise CatalogueError(f"The object referenced by {uri} is not a JSON Schema")

        return schema

    @contextmanager
    def session(self, session: Hashable = None) -> ContextManager[Hashable]:
        if session is None:
            session = uuid.uuid4()

        if session in self._schema_cache:
            raise CatalogueError("session is already in use")

        try:
            yield session
        finally:
            self._schema_cache.pop(session, None)
