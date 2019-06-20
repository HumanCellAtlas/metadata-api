from unittest import TestCase

from ingest.template.schema_template import SchemaTemplate


import json

# class TestPropertyMigrations(TestCase):
#     def setUp(self):
#         with open('cans/schemas/cell_suspension_ex_v1.json') as json_file:
#             self.metadata_json = json.load(json_file)
#
#         with open('cans/schemas/cell_suspension_schema.json') as json_file:
#             self.schema = json.load(json_file)
#
#         with open('cans/schemas/property_migrations.json') as json_file:
#             self.migrations = json.load(json_file)
#
#         self.schema_api = SchemaTemplate(json_schema_docs=[self.schema], migrations=self.migrations["migrations"])
#
#     def test_look_up(self):
#         # given:
#         fq_key = 'cell_suspension.selected_cell_type.text'
#
#
#
#         data = self.property_migrations.look_up(self.metadata_json, fq_key)
#         self.assertEqual(data[0], "arcuate artery endothelial cell")
#
#     def test_get_version(self):
#         version = self.property_migrations.get_version(self.metadata_json)
#         self.assertEqual('13.1.1', version)
#
#     def test_construct_key(self):
#         fq_key = 'cell_suspension.selected_cell_type'
#         migration_object = {
#              "source_schema": "cell_suspension",
#              "property": "selected_cell_type",
#              "target_schema": "cell_suspension",
#              "replaced_by": "selected_cell_types",
#              "effective_from": "13.0.0",
#              "reason": "Schema consistency update",
#              "type": "renamed property"
#         }
#         new_fq_key = self.property_migrations.construct_key(migration_object)
#
#         self.assertEqual(new_fq_key, 'cell_suspension.selected_cell_types')
#
#     def test_look_up_from_data(self):
#         fq_key = 'cell_suspension.biomaterial_core.biomaterial_id'
#         data = self.property_migrations._look_up(self.metadata_json, fq_key)
#         self.assertEqual(data, 'cell_ID_1')
