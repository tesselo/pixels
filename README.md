# Pixels
A globel pixel grabber engine.

With a simple [documentation](docs/index.md).

## Environment
For search in scihub `ESA_SCIHUB_USERNAME` and `ESA_SCIHUB_PASSWORD`.

For batch jobs `AWS_S3_BUCKET` and `PROJECT_ID`.

## Run tests
```
PYTHONPATH=. python tests/test_pixels.py
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
zappa update dev
```

```shell
# Deploy production.
workon pixels-deploy-production
zappa update production
```
