from abc import ABC, abstractmethod
from collections import defaultdict
from itertools import chain
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Set, Type, TypeVar, Union
from uuid import UUID
import warnings

from dataclasses import dataclass, field

from humancellatlas.data.metadata.age_range import AgeRange

# A few helpful type aliases
#
from humancellatlas.data.metadata.lookup import lookup, ontology_label, resolve_local_property, get_document_version, get_schema_name

UUID4 = UUID
AnyJSON2 = Union[str, int, float, bool, None, Mapping[str, Any], List[Any]]
AnyJSON1 = Union[str, int, float, bool, None, Mapping[str, AnyJSON2], List[AnyJSON2]]
AnyJSON = Union[str, int, float, bool, None, Mapping[str, AnyJSON1], List[AnyJSON1]]
JSON = Mapping[str, AnyJSON]


@dataclass(init=False)
class Entity:
    json: JSON = field(repr=False)
    document_id: UUID4

    @classmethod
    def from_json(cls, json: JSON, **kwargs):
        content = json.get('content', json)
        described_by = content['describedBy']
        schema_name = described_by.rpartition('/')[2]
        try:
            sub_cls = entity_types[schema_name]
        except KeyError:
            raise TypeLookupError(described_by)
        return sub_cls(json, **kwargs)

    def __init__(self, json: JSON) -> None:
        super().__init__()
        self.json = json
        provenance = json.get('hca_ingest') or json['provenance']
        self.document_id = UUID4(provenance['document_id'])

    @property
    def address(self):
        return self.schema_name + '@' + str(self.document_id)

    @property
    def schema_name(self):
        return schema_names[type(self)]

    def accept(self, visitor: 'EntityVisitor') -> None:
        visitor.visit(self)


# A type variable for subtypes of Entity
#
E = TypeVar('E', bound=Entity)


class TypeLookupError(Exception):

    def __init__(self, described_by: str) -> None:
        super().__init__(f"No entity type for schema URL '{described_by}'")


class EntityVisitor(ABC):

    @abstractmethod
    def visit(self, entity: 'Entity') -> None:
        raise NotImplementedError()


@dataclass(init=False)
class LinkedEntity(Entity, ABC):
    children: MutableMapping[UUID4, Entity] = field(repr=False)
    parents: MutableMapping[UUID4, 'LinkedEntity'] = field(repr=False)

    @abstractmethod
    def _connect_to(self, other: Entity, forward: bool) -> None:
        raise NotImplementedError()

    def __init__(self, json: JSON) -> None:
        super().__init__(json)
        self.children = {}
        self.parents = {}

    def connect_to(self, other: Entity, forward: bool) -> None:
        mapping = self.children if forward else self.parents
        mapping[other.document_id] = other
        self._connect_to(other, forward)

    def ancestors(self, visitor: EntityVisitor):
        for parent in self.parents.values():
            parent.ancestors(visitor)
            visitor.visit(parent)

    def accept(self, visitor: EntityVisitor):
        super().accept(visitor)
        for child in self.children.values():
            child.accept(visitor)


class LinkError(RuntimeError):

    def __init__(self, entity: LinkedEntity, other_entity: Entity, forward: bool) -> None:
        super().__init__(entity.address +
                         ' cannot ' + ('reference ' if forward else 'be referenced by ') +
                         other_entity.address)


@dataclass(frozen=True)
class ProjectPublication:
    title: str
    url: Optional[str]

    @classmethod
    def from_json(cls, json: JSON) -> 'ProjectPublication':
        title = lookup(json, 'project.publication_title')
        url = lookup(json, 'project.publication_url')
        return cls(title=title, url=url)

    @classmethod
    def from_json_version(cls, json: JSON, version) -> 'ProjectPublication':
        title = resolve_local_property(json, 'publication_title', 'project.publications', version)
        url = resolve_local_property(json, 'publication_url', 'project.publications', version, default=None)
        return cls(title=title, url=url)

    @property
    def publication_title(self):
        warnings.warn(f"ProjectPublication.publication_title is deprecated. "
                      f"Use ProjectPublication.title instead.", DeprecationWarning)
        return self.title

    @property
    def publication_url(self):
        warnings.warn(f"ProjectPublication.publication_url is deprecated. "
                      f"Use ProjectPublication.url instead.", DeprecationWarning)
        return self.url


@dataclass(frozen=True)
class ProjectContact:
    name: str
    email: Optional[str]
    institution: Optional[str]  # optional up to project/5.3.0/contact
    laboratory: Optional[str]
    corresponding_contributor: Optional[bool]
    project_role: Optional[str]

    @classmethod
    def from_json(cls, json: JSON) -> 'ProjectContact':
        return cls(name=lookup(json, 'project.contributors.contact_name'),
                   email=lookup(json, 'project.contributors.email'),
                   institution=lookup(json, 'project.contributors.institution'),
                   laboratory=lookup(json, 'project.contributors.laboratory'),
                   corresponding_contributor=lookup(json, 'project.contributors.corresponding_contributor'),
                   project_role=ontology_label(lookup(json, 'project.contributors.project_role', default=None)))

    @classmethod
    def from_json_version(cls, json: JSON, version) -> 'ProjectContact':
        return cls(name=resolve_local_property(json, 'contact_name', 'project.contributors', version, default=None),
                   email=resolve_local_property(json, 'email', 'project.contributors', version, default=None),
                   institution=resolve_local_property(json, 'institution', 'project.contributors', version, default=None),
                   laboratory=resolve_local_property(json, 'laboratory', 'project.contributors', version, default=None),
                   corresponding_contributor=resolve_local_property(json, 'corresponding_contributor', 'project.contributors', version, default=None),
                   project_role=ontology_label(resolve_local_property(json, 'project_role', 'project.contributors', version, default=None)))


    @property
    def contact_name(self) -> str:
        warnings.warn(f"ProjectContact.contact_name is deprecated. "
                      f"Use ProjectContact.name instead.", DeprecationWarning)
        return self.name


@dataclass(init=False)
class Project(Entity):
    project_short_name: str
    project_title: str
    project_description: Optional[str]  # optional up to core/project/5.2.2/project_core
    publications: Set[ProjectPublication]
    contributors: Set[ProjectContact]
    insdc_project_accessions: Set[str]
    geo_series_accessions: Set[str]
    array_express_accessions: Set[str]
    insdc_study_accessions: Set[str]

    def __init__(self, json: JSON) -> None:
        super().__init__(json)
        json = json.get('content', json)
        version = get_document_version(json)

        self.project_short_name = lookup(json, 'project.project_core.project_shortname')
        self.project_title = lookup(json, 'project.project_core.project_title')
        self.project_description = lookup(json, 'project.project_core.project_description')

        self.publications = set(ProjectPublication.from_json_version(publication, version)
                                for publication in lookup(json, 'project.publications', default=""))

        self.contributors = {ProjectContact.from_json_version(contributor, version)
                             for contributor in lookup(json, 'project.contributors', default=[])}

        self.insdc_project_accessions = set(lookup(json, 'project.insdc_project_accessions', default=""))
        self.geo_series_accessions = set(lookup(json, 'project.geo_series_accessions', default=""))
        self.array_express_accessions = set(lookup(json, 'project.array_express_accessions', default=""))
        self.insdc_study_accessions = set(lookup(json, 'project.insdc_study_accessions', default=""))

    @property
    def laboratory_names(self) -> set:
        warnings.warn("Project.laboratory_names is deprecated. "
                      "Use contributors.laboratory instead.", DeprecationWarning)
        return {contributor.laboratory for contributor in self.contributors if contributor.laboratory}

    @property
    def project_shortname(self) -> str:
        warnings.warn("Project.project_shortname is deprecated. "
                      "Use project_short_name instead.", DeprecationWarning)
        return self.project_short_name


@dataclass(init=False)
class Biomaterial(LinkedEntity):
    biomaterial_id: str
    ncbi_taxon_id: List[int]
    has_input_biomaterial: Optional[str]
    from_processes: MutableMapping[UUID4, 'Process'] = field(repr=False)
    to_processes: MutableMapping[UUID4, 'Process']

    def __init__(self, json: JSON) -> None:
        super().__init__(json)
        json = json.get('content', json)
        schema_name = get_schema_name(json)
        self.biomaterial_id = lookup(json, schema_name+'.biomaterial_core.biomaterial_id')
        self.ncbi_taxon_id = lookup(json, schema_name+'.biomaterial_core.ncbi_taxon_id')
        self.has_input_biomaterial = lookup(json, schema_name+'.biomaterial_core.has_input_biomaterial', default=None)
        self.from_processes = {}
        self.to_processes = {}

    def _connect_to(self, other: Entity, forward: bool) -> None:
        if isinstance(other, Process):
            if forward:
                self.to_processes[other.document_id] = other
            else:
                self.from_processes[other.document_id] = other
        else:
            raise LinkError(self, other, forward)


@dataclass(init=False)
class DonorOrganism(Biomaterial):
    genus_species: Set[str]
    diseases: Set[str]
    organism_age: str
    organism_age_unit: str
    sex: str

    def __init__(self, json: JSON):
        super().__init__(json)
        json = json.get('content', json)
        self.genus_species = {ontology_label(gs) for gs in lookup(json, 'donor_organism.genus_species')}
        self.diseases = {ontology_label(d) for d in lookup(json, 'donor_organism.disease', default=[])}
        self.organism_age = lookup(json, 'donor_organism.organism_age', default=None)
        self.organism_age_unit = ontology_label(lookup(json, 'donor_organism.organism_age_unit', default=None))
        self.sex = lookup(json, 'donor_organism.biological_sex')

    @property
    def organism_age_in_seconds(self) -> Optional[AgeRange]:
        if self.organism_age and self.organism_age_unit:
            return AgeRange.parse(self.organism_age, self.organism_age_unit)
        else:
            return None

    @property
    def biological_sex(self):
        warnings.warn(f"DonorOrganism.biological_sex is deprecated. "
                      f"Use DonorOrganism.sex instead.", DeprecationWarning)
        return self.sex

    @property
    def disease(self):
        warnings.warn(f"DonorOrganism.disease is deprecated. "
                      f"Use DonorOrganism.diseases instead.", DeprecationWarning)
        return self.diseases


@dataclass(init=False)
class SpecimenFromOrganism(Biomaterial):
    storage_method: Optional[str]
    preservation_method: Optional[str]
    diseases: Set[str]
    organ: Optional[str]
    organ_parts: Set[str]

    def __init__(self, json: JSON):
        super().__init__(json)
        json = json.get('content', json)
        self.storage_method = lookup(json, 'specimen_from_organism.preservation_storage.storage_method', default=None)
        self.preservation_method = lookup(json, 'specimen_from_organism.preservation_storage.preservation_method', default=None)
        self.diseases = {ontology_label(d) for d in lookup(json, 'specimen_from_organism.disease', default=[])}
        self.organ = ontology_label(lookup(json, 'specimen_from_organism.organ', default=None))
        self.organ_parts = {ontology_label(d) for d in lookup(json, 'specimen_from_organism.organ_parts', default=[])}

    @property
    def disease(self):
        warnings.warn(f"SpecimenFromOrganism.disease is deprecated. "
                      f"Use SpecimenFromOrganism.diseases instead.", DeprecationWarning)
        return self.diseases

    @property
    def organ_part(self):
        msg = ("SpecimenFromOrganism.organ_part has been removed. "
               "Use SpecimenFromOrganism.organ_parts instead.")
        warnings.warn(msg, DeprecationWarning)
        raise AttributeError(msg)


@dataclass(init=False)
class ImagedSpecimen(Biomaterial):
    slice_thickness: Union[float, int]

    def __init__(self, json: JSON) -> None:
        super().__init__(json)
        json = json.get('content', json)
        self.slice_thickness = lookup(json, 'imaged_specimen.slice_thickness')


@dataclass(init=False)
class CellSuspension(Biomaterial):
    estimated_cell_count: Optional[int]
    selected_cell_types: Set[str]

    def __init__(self, json: JSON) -> None:
        super().__init__(json)
        json = json.get('content', json)
        self.estimated_cell_count = lookup(json, 'cell_suspension.total_estimated_cells', default=None)
        self.selected_cell_types = {ontology_label(sct) for sct in
                                    lookup(json, 'cell_suspension.selected_cell_type', default=[])}

    @property
    def total_estimated_cells(self) -> int:
        warnings.warn(f"CellSuspension.total_estimated_cells is deprecated. "
                      f"Use CellSuspension.estimated_cell_count instead.", DeprecationWarning)
        return self.estimated_cell_count

    @property
    def selected_cell_type(self) -> Set[str]:
        warnings.warn(f"CellSuspension.selected_cell_type is deprecated. "
                      f"Use CellSuspension.selected_cell_types instead.", DeprecationWarning)
        return self.selected_cell_types


@dataclass(init=False)
class CellLine(Biomaterial):
    type: str
    model_organ: Optional[str]

    def __init__(self, json: JSON) -> None:
        super().__init__(json)
        json = json.get('content', json)
        self.type = lookup(json, 'cell_line.cell_line_type')
        self.model_organ = ontology_label(lookup(json, 'cell_line.model_organ', default=None))

    @property
    def cell_line_type(self) -> str:
        warnings.warn(f"CellLine.cell_line_type is deprecated. "
                      f"Use CellLine.type instead.", DeprecationWarning)
        return self.type



@dataclass(init=False)
class Organoid(Biomaterial):
    model_organ: str
    model_organ_part: Optional[str]

    def __init__(self, json: JSON) -> None:
        super().__init__(json)
        json = json.get('content', json)
        self.model_organ = ontology_label(lookup(json, 'organoid.model_organ', default=None))
        self.model_organ_part = ontology_label(lookup(json, 'organoid.model_organ_part', default=None))


@dataclass(init=False)
class Process(LinkedEntity):
    process_id: str
    process_name: Optional[str]
    input_biomaterials: MutableMapping[UUID4, Biomaterial] = field(repr=False)
    input_files: MutableMapping[UUID4, 'File'] = field(repr=False)
    output_biomaterials: MutableMapping[UUID4, Biomaterial]
    output_files: MutableMapping[UUID4, 'File']
    protocols: MutableMapping[UUID4, 'Protocol']

    def __init__(self, json: JSON) -> None:
        super().__init__(json)
        json = json.get('content', json)
        schema_name = get_schema_name(json)
        self.process_id = lookup(json, schema_name+'.process_core.process_id')
        self.process_name = lookup(json, schema_name+'.process.process_core.process_name', default=None)
        self.input_biomaterials = {}
        self.input_files = {}
        self.output_biomaterials = {}
        self.output_files = {}
        self.protocols = {}

    def _connect_to(self, other: Entity, forward: bool) -> None:
        if isinstance(other, Biomaterial):
            biomaterials = self.output_biomaterials if forward else self.input_biomaterials
            biomaterials[other.document_id] = other
        elif isinstance(other, File):
            files = self.output_files if forward else self.input_files
            files[other.document_id] = other
        elif isinstance(other, Protocol):
            if forward:
                self.protocols[other.document_id] = other
            else:
                raise LinkError(self, other, forward)
        else:
            raise LinkError(self, other, forward)

    def is_sequencing_process(self):
        return any(isinstance(pl, SequencingProtocol) for pl in self.protocols.values())


@dataclass(init=False)
class AnalysisProcess(Process):
    pass


@dataclass(init=False)
class DissociationProcess(Process):

    def __init__(self, json: JSON) -> None:
        warnings.warn(f"{type(self)} is deprecated", DeprecationWarning)
        super().__init__(json)


@dataclass(init=False)
class EnrichmentProcess(Process):

    def __init__(self, json: JSON) -> None:
        warnings.warn(f"{type(self)} is deprecated", DeprecationWarning)
        super().__init__(json)


@dataclass(init=False)
class LibraryPreparationProcess(Process):
    library_construction_approach: str

    def __init__(self, json: JSON):
        warnings.warn(f"{type(self)} is deprecated", DeprecationWarning)
        super().__init__(json)
        json = json.get('content', json)
        self.library_construction_approach = lookup(json, 'library_preparation_protocol.library_construction_approach')


@dataclass(init=False)
class SequencingProcess(Process):
    instrument_manufacturer_model: str

    def __init__(self, json: JSON):
        warnings.warn(f"{type(self)} is deprecated", DeprecationWarning)
        super().__init__(json)
        json = json.get('content', json)
        self.instrument_manufacturer_model = ontology_label(lookup(json, 'sequencing_process.instrument_manufacturer_model'))

    def is_sequencing_process(self):
        return True


@dataclass(frozen=True)
class ImagingTarget:
    assay_type: str

    @classmethod
    def from_json(cls, json: JSON, described_by: str) -> 'ImagingTarget':
        json['describedBy'] = described_by
        assay_type = ontology_label(lookup(json, 'imaging_target.assay_type'))
        return cls(assay_type=assay_type)


@dataclass(init=False)
class Protocol(LinkedEntity):
    protocol_id: str
    protocol_name: Optional[str]

    def __init__(self, json: JSON) -> None:
        super().__init__(json)
        json = json.get('content', json)
        schema_name = get_schema_name(json)
        self.protocol_id = lookup(json, schema_name+'.protocol_core.protocol_id')
        self.protocol_name = lookup(json, schema_name+'.protocol_core.protocol_name', default=None)

    def _connect_to(self, other: Entity, forward: bool) -> None:
        if isinstance(other, Process) and not forward:
            pass  # no explicit, typed back reference
        else:
            raise LinkError(self, other, forward)


@dataclass(init=False)
class LibraryPreparationProtocol(Protocol):
    library_construction_method: str

    def __init__(self, json: JSON) -> None:
        super().__init__(json)
        json = json.get('content', json)
        self.library_construction_method = ontology_label(
            lookup(json, 'library_preperation_protocol.library_construction_approach', default=None)
        )

    @property
    def library_construction_approach(self) -> str:
        warnings.warn(f"LibraryPreparationProtocol.library_construction_approach is deprecated. "
                      f"Use LibraryPreparationProtocol.library_construction_method instead.", DeprecationWarning)
        return self.library_construction_method


@dataclass(init=False)
class SequencingProtocol(Protocol):
    instrument_manufacturer_model: str
    paired_end: Optional[bool]

    def __init__(self, json: JSON):
        super().__init__(json)
        json = json.get('content', json)
        self.instrument_manufacturer_model = ontology_label(
            lookup(json, 'sequencing_protocol.instrument_manufacturer_model')
        )
        self.paired_end = lookup(json, 'sequencing_protocol.paired_end')


@dataclass(init=False)
class AnalysisProtocol(Protocol):
    pass


@dataclass(init=False)
class AggregateGenerationProtocol(Protocol):
    pass


@dataclass(init=False)
class CollectionProtocol(Protocol):
    pass


@dataclass(init=False)
class DifferentiationProtocol(Protocol):
    pass


@dataclass(init=False)
class DissociationProtocol(Protocol):
    pass


@dataclass(init=False)
class EnrichmentProtocol(Protocol):
    pass


@dataclass(init=False)
class IpscInductionProtocol(Protocol):
    pass


@dataclass(init=False)
class ImagingProtocol(Protocol):
    target: List[ImagingTarget]  # A list so all the ImagingTarget objects can be tallied when indexed

    def __init__(self, json: JSON):
        super().__init__(json)
        json = json.get('content', json)
        described_by = json['describedBy']
        self.target = [ImagingTarget.from_json(target, described_by) for target in lookup(json, 'imaging_protocol.target')]

@dataclass(init=False)
class ImagingPreparationProtocol(Protocol):
    pass


@dataclass
class ManifestEntry:
    content_type: str
    crc32c: str
    indexed: bool
    name: str
    s3_etag: str
    sha1: str
    sha256: str
    size: int
    url: str  # only populated if bundle was requested with `directurls` or `directurls` set
    uuid: UUID4
    version: str

    @classmethod
    def from_json(cls, json: JSON):
        kwargs = dict(json)
        kwargs['content_type'] = kwargs.pop('content-type')
        kwargs['uuid'] = UUID4(json['uuid'])
        kwargs.setdefault('url')
        return cls(**kwargs)


@dataclass(init=False)
class File(LinkedEntity):
    format: str
    from_processes: MutableMapping[UUID4, Process] = field(repr=False)
    to_processes: MutableMapping[UUID4, Process]
    manifest_entry: ManifestEntry

    def __init__(self, json: JSON, manifest: Mapping[str, ManifestEntry]):
        super().__init__(json)
        json = json.get('content', json)
        schema_name = get_schema_name(json)
        core = json['file_core']
        self.format = lookup(json, schema_name+'.file_core.file_format')
        self.manifest_entry = manifest[core['file_name']]

        self.from_processes = {}
        self.to_processes = {}

    def _connect_to(self, other: Entity, forward: bool) -> None:
        if isinstance(other, Process):
            if forward:
                self.to_processes[other.document_id] = other
            else:
                self.from_processes[other.document_id] = other
        else:
            raise LinkError(self, other, forward)

    @property
    def file_format(self) -> str:
        warnings.warn(f"File.file_format is deprecated. "
                      f"Use File.format instead.", DeprecationWarning)
        return self.format


@dataclass(init=False)
class SequenceFile(File):
    read_index: str
    lane_index: Optional[str]

    def __init__(self, json: JSON, manifest: Mapping[str, ManifestEntry]):
        super().__init__(json, manifest)
        json = json.get('content', json)
        self.read_index = lookup(json, 'sequence_file.read_index', default=None)
        self.lane_index = lookup(json, 'sequence_file.lane_index', default=None)


@dataclass(init=False)
class SupplementaryFile(File):
    pass


@dataclass(init=False)
class AnalysisFile(File):
    pass


@dataclass(init=False)
class ReferenceFile(File):
    pass


@dataclass(init=False)
class ImageFile(File):
    pass


@dataclass
class Link:
    source_id: UUID4
    source_type: str
    destination_id: UUID4
    destination_type: str

    @classmethod
    def from_json(cls, json: JSON) -> Iterable['Link']:
        if 'source_id' in json:
            # v5
            yield cls(source_id=UUID4(json['source_id']),
                      source_type=json['source_type'],
                      destination_id=UUID4(json['destination_id']),
                      destination_type=json['destination_type'])
        else:
            # vx
            process_id = UUID4(json['process'])
            for source_id in json['inputs']:
                yield cls(source_id=UUID4(source_id),
                          source_type=json['input_type'],
                          destination_id=process_id,
                          destination_type='process')
            for destination_id in json['outputs']:
                yield cls(source_id=process_id,
                          source_type='process',
                          destination_id=UUID4(destination_id),
                          destination_type=json['output_type'])
            for protocol in json['protocols']:
                yield cls(source_id=process_id,
                          source_type='process',
                          destination_id=UUID4(protocol['protocol_id']),
                          destination_type=protocol['protocol_type'])


@dataclass(init=False)
class Bundle:
    uuid: UUID4
    version: str
    projects: MutableMapping[UUID4, Project]
    biomaterials: MutableMapping[UUID4, Biomaterial]
    processes: MutableMapping[UUID4, Process]
    protocols: MutableMapping[UUID4, Protocol]
    files: MutableMapping[UUID4, File]

    manifest: MutableMapping[str, ManifestEntry]
    entities: MutableMapping[UUID4, Entity] = field(repr=False)
    links: List[Link]

    def __init__(self, uuid: str, version: str, manifest: List[JSON], metadata_files: Mapping[str, JSON]):
        self.uuid = UUID4(uuid)
        self.version = version
        self.manifest = {m.name: m for m in map(ManifestEntry.from_json, manifest)}

        def from_json(core_cls: Type[E], json_entities: List[JSON], **kwargs) -> MutableMapping[UUID4, E]:
            entities = (core_cls.from_json(entity, **kwargs) for entity in json_entities)
            return {entity.document_id: entity for entity in entities}

        if 'project.json' in metadata_files:

            def from_json_v5(core_cls: Type[E], file_name, key=None, **kwargs) -> MutableMapping[UUID4, E]:
                file_content = metadata_files.get(file_name)
                if file_content:
                    json_entities = file_content[key] if key else [file_content]
                    return from_json(core_cls, json_entities, **kwargs)
                else:
                    return {}

            self.projects = from_json_v5(Project, 'project.json')
            self.biomaterials = from_json_v5(Biomaterial, 'biomaterial.json', 'biomaterials')
            self.processes = from_json_v5(Process, 'process.json', 'processes')
            self.protocols = from_json_v5(Protocol, 'protocol.json', 'protocols')
            self.files = from_json_v5(File, 'file.json', 'files', manifest=self.manifest)

        elif 'project_0.json' in metadata_files:

            json_by_core_cls: MutableMapping[Type[E], List[JSON]] = defaultdict(list)
            for file_name, json in metadata_files.items():
                assert file_name.endswith('.json')
                schema_name, _, suffix = file_name[:-5].rpartition('_')
                if schema_name and suffix.isdigit():
                    entity_cls = entity_types[schema_name]
                    core_cls = core_types[entity_cls]
                    json_by_core_cls[core_cls].append(json)

            def from_json_vx(core_cls: Type[E], **kwargs) -> MutableMapping[UUID4, E]:
                json_entities = json_by_core_cls[core_cls]
                return from_json(core_cls, json_entities, **kwargs)

            self.projects = from_json_vx(Project)
            self.biomaterials = from_json_vx(Biomaterial)
            self.processes = from_json_vx(Process)
            self.protocols = from_json_vx(Protocol)
            self.files = from_json_vx(File, manifest=self.manifest)

        else:

            raise RuntimeError('Unable to detect bundle structure')

        self.entities = {**self.projects, **self.biomaterials, **self.processes, **self.protocols, **self.files}

        links = metadata_files['links.json']['links']
        self.links = list(chain.from_iterable(map(Link.from_json, links)))

        for link in self.links:
            source_entity = self.entities[link.source_id]
            destination_entity = self.entities[link.destination_id]
            assert isinstance(source_entity, LinkedEntity)
            assert isinstance(destination_entity, LinkedEntity)
            source_entity.connect_to(destination_entity, forward=True)
            destination_entity.connect_to(source_entity, forward=False)

    def root_entities(self) -> Mapping[UUID4, LinkedEntity]:
        roots = {}

        class RootFinder(EntityVisitor):

            def visit(self, entity: Entity) -> None:
                if isinstance(entity, LinkedEntity) and not entity.parents:
                    roots[entity.document_id] = entity

        visitor = RootFinder()
        for entity in self.entities.values():
            entity.accept(visitor)

        return roots

    @property
    def specimens(self) -> List[SpecimenFromOrganism]:
        return [s for s in self.biomaterials.values() if isinstance(s, SpecimenFromOrganism)]

    @property
    def sequencing_input(self) -> List[Biomaterial]:
        return [bm for bm in self.biomaterials.values()
                if any(ps.is_sequencing_process() for ps in bm.to_processes.values())]

    @property
    def sequencing_output(self) -> List[SequenceFile]:
        return [f for f in self.files.values()
                if isinstance(f, SequenceFile)
                and any(ps.is_sequencing_process() for ps in f.from_processes.values())]


entity_types = {
    # Biomaterials
    'donor_organism': DonorOrganism,
    'specimen_from_organism': SpecimenFromOrganism,
    'cell_suspension': CellSuspension,
    'cell_line': CellLine,
    'organoid': Organoid,
    'imaged_specimen': ImagedSpecimen,

    # Files
    'analysis_file': AnalysisFile,
    'reference_file': ReferenceFile,
    'sequence_file': SequenceFile,
    'supplementary_file': SupplementaryFile,
    'image_file': ImageFile,

    # Protocols
    'protocol': Protocol,
    'analysis_protocol': AnalysisProtocol,
    'aggregate_generation_protocol': AggregateGenerationProtocol,
    'collection_protocol': CollectionProtocol,
    'differentiation_protocol': DifferentiationProtocol,
    'dissociation_protocol': DissociationProtocol,
    'enrichment_protocol': EnrichmentProtocol,
    'ipsc_induction_protocol': IpscInductionProtocol,
    'imaging_protocol': ImagingProtocol,
    'library_preparation_protocol': LibraryPreparationProtocol,
    'sequencing_protocol': SequencingProtocol,
    'imaging_preparation_protocol': ImagingPreparationProtocol,

    'project': Project,

    # Processes
    'process': Process,
    'analysis_process': AnalysisProcess,
    'dissociation_process': DissociationProcess,
    'enrichment_process': EnrichmentProcess,
    'library_preparation_process': LibraryPreparationProcess,
    'sequencing_process': SequencingProcess
}

schema_names = {
    v: k for k, v in entity_types.items()
}

core_types = {
    entity_type: core_type
    for core_type in (Project, Biomaterial, Process, Protocol, File)
    for entity_type in entity_types.values()
    if issubclass(entity_type, core_type)
}

assert len(entity_types) == len(schema_names), "The mapping from schema name to entity type is not bijective"
