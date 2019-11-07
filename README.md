[![Build Status](https://travis-ci.org/HumanCellAtlas/metadata-api.svg?branch=develop)](https://travis-ci.org/HumanCellAtlas/metadata-api)
[![Coverage Status](https://coveralls.io/repos/github/HumanCellAtlas/metadata-api/badge.svg?branch=develop)](https://coveralls.io/github/HumanCellAtlas/metadata-api?branch=develop)

The HumanCellAtlas metadata API
===============================

## Overview

Metadata API serves as a light-weight wrapper library around the JSON metadata 
in HCA data bundles. This library serves two purposes: providing convenient 
programmatic access to a subset of metadata attributes as well as decoupling 
clients from schema changes that would break direct access to the metadata.

## Requirements

- Python 3.6

## Installation

Version 1.0 will be on PyPI but until then we need to install from GitHub: 

```
$ virtualenv -p python3 foo
$ source foo/bin/activate
$ pip install "git+git://github.com/HumanCellAtlas/metadata-api@master#egg=hca-metadata-api[dss]"
```

You can omit `[dss]` at the end of the `pip` invocation if you don't need
the download helper this library provides and don't want to pull in the HCA CLI
distribution the helper depends on.

## Testing

To run unit tests, run 
```
$ make test
```


## Terminology

- Document
  - A JSON data file containing metadata details about Project entities. 
  Examples of documents include those that represent biomaterials 
  (specimens or cell suspensions), analysis processes, protocols, sequence 
  files, and the overall project.
- LinkedEntity
  - Baseclass to all Biomaterial, Process, Protocol, and File objects, allowing
  them to be linked in a tree structure representing the interconnected 
  structure of the Project's documents.
- Project
  - An experiment or study represented by a collection of documents.
- Bundle
  - A collection of documents belonging to one or more projects.
- Manifest
  - A list of documents contained within a bundle.


## Helper Functions & Classes

Metadata API offers helper functions and classes useful in the retrieval of 
bundle metadata from the HCA Data Store Service (DSS).

### dss_client()

```
from humancellatlas.data.metadata.helpers.dss import dss_client
client = dss_client()
```

`dss_client()` returns a DSSClient object, a client for the Data Storage 
Service API. By default the client will be configured for the `prod` 
deployment, or a deployment can be specified using the `deployment` parameter 
set to `dev`, `integration`, `staging`, or `prod`.

### download_bundle_metadata()

```
from humancellatlas.data.metadata.helpers.dss import download_bundle_metadata
version, manifest, metadata_files = download_bundle_metadata(client=dss_client(), replica='aws', uuid=bundle_uuid)
```

`download_bundle_metadata()` downloads the metadata of a given bundle from the 
DSS. Given a DSSClient object, the name of a replica (eg. 'aws') and the UUID 
of a bundle this function will request data from DSS and return a tuple 
consisting of the bundle version, a manifest listing entries for all files in 
the bundle, and a dictionary mapping the file name of each metadata file in the 
bundle to the JSON contents of that file.

### Bundle class

```
from humancellatlas.data.metadata.api import Bundle
bundle = Bundle(BUNDLE_UUID, version, manifest, metadata_files)
```

The `Bundle` class provides an organized view of a bundle's metadata. 

Within a `Bundle` object the JSON documents are grouped by type and available 
from the instance variables `projects`, `biomaterials`, `processes`, 
`protocols`, and `files`. Additional properties `specimens`, `sequencing_input` 
and `sequencing_output` return a list of the matching `Biomaterial` or 
`SequenceFile` documents. 

To facilitate traversal of the entities within a `Bundle` the method 
`root_entities()` provides a collection of the root nodes in the tree. Using the
`children` variable in each node document the graph can be traversed down each
branch of the tree.


## Example Usage

```
from humancellatlas.data.metadata.api import Bundle
from humancellatlas.data.metadata.helpers.dss import download_bundle_metadata, dss_client

bundle_uuid = 'cf813e6b-dc70-4374-9759-b5780618c234'
bundle_version = '2019-05-15T222432.558000Z'

version, manifest, metadata_files = download_bundle_metadata(client=dss_client(),
                                                             replica='aws',
                                                             uuid=bundle_uuid,
                                                             version=bundle_version)

bundle = Bundle(bundle_uuid, bundle_version, manifest, metadata_files)

# Iterate over all biomaterial documents in the bundle
print('-- Biomaterials --')
for biomaterial in bundle.biomaterials.values():
    print('Biomaterial: ' + type(biomaterial).__name__)

# Iterate over all file documents in the bundle
print('-- Files --')
for file in bundle.files.values():
    print('File: ' + type(file).__name__ + ' ' + file.format)

def visit_children(node, depth=0):
    print(' ' * depth, end='')
    print(type(node).__name__, '@', node.document_id)
    for child in node.children.values():
        visit_children(child, depth + 1)

# Iterate over the full graph of documents starting from the root nodes
print('-- Full Graph --')
for root in bundle.root_entities().values():
    visit_children(root)
```

### Example Usage (output)

```
-- Biomaterials --
Biomaterial: CellSuspension
Biomaterial: SpecimenFromOrganism
Biomaterial: DonorOrganism
-- Files --
File: SequenceFile fastq.gz
File: SequenceFile fastq.gz
File: SupplementaryFile pdf
File: SupplementaryFile pdf
File: SupplementaryFile pdf
-- Full Graph --
DonorOrganism @ 63818269-c4d9-429b-85a3-db39c0dd7fa0
 Process @ 453a352c-94fb-4d3b-b609-df1e7abf8c09
  SpecimenFromOrganism @ 74eb3cb5-918a-49fc-9e15-3ac49fd54caf
   Process @ c595e6b3-958a-4b9c-93a9-2193d2862d0a
    CellSuspension @ 3b9f81fc-54af-41af-ac70-46c4f3f7c51a
     Process @ c2747285-af25-4c8f-938b-b6e59b527283
      SequenceFile @ 24ef0080-7ec4-4a65-83e7-5eddde983d5d
      SequenceFile @ 558da709-6fe4-4416-8104-fcd76ec5b239
      LibraryPreparationProtocol @ 5b503dcb-dca6-4e4f-988b-f7100c030dc5
      SequencingProtocol @ eca2ab79-ad61-411f-815a-4f6d936d992b
    DissociationProtocol @ fcba26aa-658c-4120-ab31-cc5a5a00f759
    EnrichmentProtocol @ 92b275e0-a62f-4b49-84f8-cb89f489f4a7
SupplementaryFile @ e738a267-87fc-4070-abc7-b3be6442c6d0
SupplementaryFile @ 01a1d04b-05d0-4904-b627-68b0dc02bc17
SupplementaryFile @ a06cb5d5-2675-4d64-aeb8-79e0103715f3
```