#!/usr/bin/env python


from humancellatlas.data.metadata.helpers.dss import download_bundle_metadata, dss_client
from humancellatlas.data.metadata.api import Bundle
from humancellatlas.data.metadata.helpers.json import as_json
from humancellatlas.data.metadata.api import EntityVisitor, CellSuspension
from humancellatlas.data.metadata.lookup import lookup, ontology_label

import json

BUNDLE_UUID = '1f578cdc-144a-44f1-936c-52fbbc6f71b8'

client = dss_client()  # Create a default dss cient
version, manifest, metadata_files = download_bundle_metadata(client, 'aws', BUNDLE_UUID)

bundle = Bundle(BUNDLE_UUID, version, manifest, metadata_files)

root_entities = bundle.root_entities() # get the root entities in the bundle

donor = next(iter(root_entities.values())).json # get a single donor as json

print(lookup(donor, 'donor_organism.sex')) # retrieves value out of json

for bm in bundle.biomaterials.values():

    print(type(bm))
    if isinstance(bm, CellSuspension):
        print (lookup(bm.json, "cell_suspension.total_estimated_cells"))
        print (lookup(bm.json, "cell_suspension.estimated_cell_count"))
