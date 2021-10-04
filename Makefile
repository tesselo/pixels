.PHONY: help Makefile

.PHONY: install dev_install upgrade_dependencies upgrade_batch_dependencies

install:
	pip install -r requirements.txt

dev_install: install
	pip install -r dev_requirements.txt
	pre-commit install

upgrade_dependencies: dev_install
	pip install pip-tools
	pip-compile --upgrade --output-file ./requirements.txt requirements.in
	pip-compile --upgrade --output-file ./dev_requirements.txt dev_requirements.in

upgrade_batch_dependencies: dev_install
	pip-compile --upgrade --output-file ./batch/docker/tensorflow_requirements.txt ./batch/docker/tensorflow_requirements.in
	pip-compile --upgrade --output-file ./batch/docker/requirements.txt ./batch/docker/requirements.in
