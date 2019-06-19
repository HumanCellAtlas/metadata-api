from ingest.template.schema_template import SchemaTemplate, UnknownKeyException


class PropertyMigrations:
    def __init__(self, schema_api):
        self.schema_api = schema_api

    # TODO: temporary lookup from data
    # should use the rolando's lookup
    def _look_up(self, metadata_json, new_fq_key):
        split_key = new_fq_key.split(".")
        copy_metadata = metadata_json
        value = []
        for key in split_key:
            if key in copy_metadata:
                copy_metadata = copy_metadata[key]
                if isinstance(copy_metadata, list):
                    for obj in copy_metadata:
                        if key in obj:
                            value.append(obj[key])
                    return value
        return copy_metadata

    def find_migration_object(self, fq_key, version):
        schema_template = SchemaTemplate()
        backtrack_fq_key = ""
        while True:
            try:
                migration_object = schema_template.lookup_migration(fq_key,
                                                                    version)
                return migration_object, backtrack_fq_key
            except UnknownKeyException:
                fq_key = fq_key.split(".")
                backtrack_fq_key = fq_key.pop() + "." + backtrack_fq_key
                fq_key = ".".join(fq_key)
                if not "." in fq_key:
                    break
    # TODO Add warnings if data or field is outdated

    def look_up(self, metadata_json, fq_key):
        version = self._get_version(metadata_json)
        new_fq_key = self.get_latest_key(fq_key, version)
        return self._look_up(metadata_json, new_fq_key)

    def get_latest_key(self, fq_key, version):
        migration_object, backtrack = self._find_migration_object(fq_key, version)
        new_fq_key = migration_object.get('replaced_by')
        new_fq_key += "." + backtrack
        return new_fq_key

    def construct_key(self, migration_object):
        concrete_type = migration_object.get('source_schema')
        replaced_by = migration_object.get('replaced_by')

        return f'{concrete_type}.{replaced_by}'

    def get_version(self, metadata_json):
        if 'schema_version' in metadata_json:
            return metadata_json['schema_version']
        return metadata_json['describedBy'].split("/")[-2]
