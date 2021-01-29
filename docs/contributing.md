# Contributing
Contribution guidelines.

## Install dependencies
Install the requirements and dev requirements.

```
pip install -r requirements.txt
pip install -r requirements_dev.txt
```

## Testing
All new code contributions should be covered by unit tests. We will
progressively improve the test suite.

To run the test suite, install the dev dependencies and run pytest like so:
```shell
pytest tests
```

## Code quality
Ensure code quality using black, isort, and flake8. To do so, run

```shell
# Autoformat code with black.
black .
# Automatically sort imports.
isort .
# Ensure PEP8 compatibility.
flake8
```

## Create documentation
Docstrings should be written for all public functions following the
[numpydoc](https://numpydoc.readthedocs.io/en/latest/format.html) docstring
style. All docstrings will automatically be included in the reference section of
this documentation.

To build the documentation locally, run the make command and open the
`build/html/index.html` file in the resulting build directory.
```shell
make html
```

## Deployment
Deployment needs to be done through virtualenvs that have the minimal number of
libraries installed to have slim lambda packages.

```shell
# Remove pyc files before deployment.
find ./ -name "*.pyc" -exec rm -f {} \;
```

```shell
# Deploy dev.
workon pixels-deploy-dev
./deploy.sh dev
```

```shell
# Deploy production.
workon pixels-deploy-production
./deploy.sh production
```
