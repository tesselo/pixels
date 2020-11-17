# Pixels
A globel pixel grabber engine.

With a simple [documentation](docs/index.md).

Copyright 2020 Tesselo - Space Mosaic Lda. All rights reserved.

## Environment
For search in scihub `ESA_SCIHUB_USERNAME` and `ESA_SCIHUB_PASSWORD`.

For batch jobs `AWS_S3_BUCKET` and `PIXELS_PROJECT_ID`.

## Run tests
Pip install pytests, then run
```
pytest tests
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
