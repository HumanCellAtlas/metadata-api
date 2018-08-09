## The HumanCellAtlas metadata API

A light-weight wrapper library around the JSON metadata in HCA data bundles.
The library serves two purposes: providing convenient programmatic access to a
subset of metadata attributes as well as decoupling clients from schema changes
that would break direct access to the metadata.


## Installation

Version 1.0 will be on PyPY but until then we need to install from GitHub: 

```
virtualenv -p python3 foo
source foo/bin/activate
pip install git+git://github.com/HumanCellAtlas/metadata-api@master#egg=hca-metadata-api[dss]
```

You can omit `[dss]` at the end of the `pip` invocation if you don't need
the download helper this library provides and don't want to pull in the HCA CLI
distribution the helper depends on.
