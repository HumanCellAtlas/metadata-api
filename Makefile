SHELL=/bin/bash

ifneq ($(shell python -c "import sys; print(hasattr(sys, 'real_prefix'))"),True)
$(error Looks like no virtualenv is active)
endif

ifneq ($(shell python -c "import sys; print(sys.version_info >= (3,6))"),True)
$(error Looks like Python 3.6 is not installed or active in the current virtualenv)
endif

install:
	pip install -e .[dss,test,coverage,examples]

travis_install:
	pip install -U setuptools>=40.1.0 pip==19.0.3
	pip install -e .[dss,test,coverage]

test: install
	coverage run -m unittest discover -vs test

examples: install
	jupyter-notebook
