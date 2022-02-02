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
#   Code Checks
#
.PHONY: pre-commit check coverage

pre-commit:
	pre-commit run -a

coverage:
	python -m pytest --cov=pixels --cov-report term --cov-report html:reports/coverage-integration --cov-report term:skip-covered

check: pre-commit coverage


open-coverage:
	xdg-open reports/coverage-integration/index.html
#
#   Extended Reports
#
.PHONY: smells security complexity check-advanced check-extended

smells:
	semgrep --config=p/r2c-ci --config=p/python

security:
	bandit -r pixels

complexity:
	wily build pixels
	wily report pixels

doc-style:
	pydocstyle batch/runpixels.py pixels

check-advanced: smells security
check-picky: complexity doc-style
check-extended: check check-advanced check-picky

#
#   Code Checks auto-fix
#
.PHONY: black

black:
	python -m black  -tpy38 batch pixels tests *.py
