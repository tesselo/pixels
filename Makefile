.PHONY: help Makefile

.PHONY: install dev_install upgrade_dependencies upgrade_batch_dependencies

cli_install:
	pip install -e .

install:
	pip install -r requirements.txt

dev_install: install
	pip install -r dev_requirements.txt
	pre-commit install
	pre-commit install --hook-type commit-msg

upgrade_dependencies: dev_install
	pip install pip-tools
	pip-compile --upgrade --output-file ./requirements.txt requirements.in
	pip-compile --upgrade --output-file ./dev_requirements.txt dev_requirements.in

upgrade_batch_dependencies: dev_install
	pip-compile --upgrade --output-file ./batch/docker/tensorflow_requirements.txt ./batch/docker/tensorflow_requirements.in
	pip-compile --upgrade --output-file ./batch/docker/requirements.txt ./batch/docker/requirements.in

#
#   Extended Reports
#
.PHONY: coverage

coverage:
	python -m pytest --cov=pixels --cov-report term --cov-report html:reports/coverage-integration --cov-report term:skip-covered


#
#   Code Checks
#
.PHONY: pre-commit check semgrep

pre-commit:
	pre-commit run -a

check: pre-commit coverage

semgrep:
	semgrep --config=p/r2c-ci --config=p/python

check-extended: check semgrep
#
#   Code Checks auto-fix
#
.PHONY: black

black:
	python -m black -l79 -tpy38 batch pixels tests *.py
