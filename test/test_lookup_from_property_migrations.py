from unittest import TestCase

from ingest.template.schema_template import SchemaTemplate

from humancellatlas.data.metadata.property_migrations import PropertyMigrations


class TestPropertyMigrations(TestCase):
    def setUp(self):
        self.metadata_json = {
            "describedBy": "https://schema.dev.data.humancellatlas.org/type/biomaterial/13.1.1/cell_suspension",
            "schema_type": "biomaterial",
            "biomaterial_core": {
                "biomaterial_id": "cell_ID_1",
                "biomaterial_name": "This is a dummy cell",
                "biomaterial_description": "This is a dummy donor cell",
                "ncbi_taxon_id": [
                    9606
                ],
                "genotype": "DRB1 0401 protective allele",
                "supplementary_files": [
                    "metadata_dog.png"
                ],
                "biosamples_accession": "SAMN00000000",
                "insdc_sample_accession": "SRS0000000"
            },
            "cell_morphology": {
                "cell_morphology": "adherent cells, form single layer colonies",
                "cell_size": "20-30",
                "cell_size_unit": {
                    "text": "micrometer",
                    "ontology": "UO:0000017",
                    "ontology_label": "micrometer"
                },
                "percent_cell_viability": 98.7,
                "cell_viability_method": "Fluorescein diacetate hydrolysis assay",
                "cell_viability_result": "pass",
                "percent_necrosis": 10
            },
            "genus_species": [{
                "text": "Homo sapiens",
                "ontology": "NCBITaxon:9606",
                "ontology_label": "Homo sapiens"
            }],
            "selected_cell_types": {
                "text": "arcuate artery endothelial cell",
                "ontology": "CL:1001213",
                "ontology_label": "arcuate artery endothelial cell"
            },
            "estimated_cell_count": 1,
            "plate_based_sequencing": {
                "plate_label": "2217",
                "well_label": "A1",
                "well_quality": "OK"
            },
            "provenance": {
                "document_id": "6214909b-77b1-4cf0-8e6b-84140d63797b",
                "submission_date": "2019-06-17T16:07:18.046Z",
                "update_date": "2019-06-17T16:07:27.423Z"
            }
        }
        # TODO check if it's possible for SchemaTemplate to only load migrations and not all latest schemas
        self.schema_api = SchemaTemplate()
        self.property_migrations = PropertyMigrations(schema_api=self.schema_api)

    def test_look_up(self):
        # given:
        fq_key = 'cell_suspension.selected_cell_type.text'

        data = self.property_migrations.look_up(self.metadata_json, fq_key)
        self.assertEqual(data[0], "arcuate artery endothelial cell")

    def test_get_version(self):
        version = self.property_migrations.get_version(self.metadata_json)
        self.assertEqual('13.1.1', version)

    def test_construct_key(self):
        fq_key = 'cell_suspension.selected_cell_type'
        migration_object = {
             "source_schema": "cell_suspension",
             "property": "selected_cell_type",
             "target_schema": "cell_suspension",
             "replaced_by": "selected_cell_types",
             "effective_from": "13.0.0",
             "reason": "Schema consistency update",
             "type": "renamed property"
        }
        new_fq_key = self.property_migrations.construct_key(migration_object)

        self.assertEqual(new_fq_key, 'cell_suspension.selected_cell_types')

    def test_look_up_from_data(self):
        fq_key = 'cell_suspension.biomaterial_core.biomaterial_id'
        data = self.property_migrations._look_up(self.metadata_json, fq_key)
        self.assertEqual(data, 'cell_ID_1')
