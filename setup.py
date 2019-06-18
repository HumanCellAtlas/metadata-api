from setuptools import setup, find_namespace_packages

setup(
    name="hca-metadata-api",
    version="1.0b20.dev1",
    license='MIT',
    install_requires=[
        'dataclasses >= 0.6', 'hca-ingest >= 0.6.6', 'jsonpath-rw'
    ],
    # Not using tests_require because that installs the test requirements into .eggs, not the virtualenv
    extras_require={
        "dss": [
            'hca == 5.2.0',
            'urllib3 >= 1.23'
        ],
        "examples": [
            'jupyter >= 1.0.0'
        ],
        "coverage": [
            'coverage',
            'coveralls'
        ],
        "test": [
            'checksumming_io == 0.0.1',
            'atomicwrites == 1.3.0',
            'more_itertools == 7.0.0'
        ]
    },
    package_dir={'': 'src'},
    packages=find_namespace_packages('src'),
    project_urls={
        "Source Code": "https://github.com/HumanCellAtlas/metadata-api",
    }
)
