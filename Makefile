SHELL=/bin/bash

ifneq ($(shell python -c "import sys; print(hasattr(sys, 'real_prefix'))"),True)
$(error Looks like no virtualenv is active)
endif

ifneq ($(shell python -c "import sys; print(sys.version_info >= (3,6))"),True)
$(error Looks like Python 3.6 is not installed or active in the current virtualenv)
endif

install_flake8:
	pip install -U flake8==3.7.8

install:
	pip install -e .[dss,test,coverage,examples]

travis_install:
	pip install -U setuptools>=40.1.0
	pip install -e .[dss,test,coverage]

test: install
	coverage run -m unittest discover -vs test

sources = src test

pep8: install_flake8
	flake8 --max-line-length=120 $(sources)

format:
	docker run \
	    --rm \
	    --volume $(CURDIR):/home/developer/metadata-api \
	    --workdir /home/developer/metadata-api rycus86/pycharm:2019.2.3 \
	    /opt/pycharm/bin/format.sh -r -settings .pycharm.style.xml -mask '*.py' $(sources)

check_clean:
	git diff --exit-code  && git diff --cached --exit-code

examples: install
	jupyter-notebook

.PHONY: install_flake8 install travis_install test pep8 format check_clean examples
