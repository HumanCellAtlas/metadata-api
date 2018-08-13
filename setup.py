from setuptools import setup, find_packages

setup(
    name="hca-metadata-api",
    version="1.0b1.dev1",
    license='MIT',
    install_requires=[
        'dataclasses >= 0.6'
    ],
    # Not using tests_require because that installs the test requirements into .eggs, not the virtualenv
    extras_require={
        "dss": [
            'hca == 4.1.0',
            'urllib3 >= 1.23'
        ],
        "examples": [
            'jupyter >= 1.0.0'
        ]
    },
    package_dir={'': 'src'},
    packages=find_packages('src'),
    project_urls={
        "Source Code": "https://github.com/HumanCellAtlas/metadata-api",
    }
)
