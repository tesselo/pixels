![pixels logo](docs/static/pixels_logo.png)

# Pixels
A global pixel grabber engine.

Copyright 2021 Tesselo - Space Mosaic Lda. All rights reserved.

## Install runtime dependencies

```
make install
```


## Install development dependencies

```
# This will also install the runtime dependencies
make dev_install
```

## Upgrade unpinned dependencies

```
make upgrade_dependencies
```

## Pre-commit hooks

We are using <https://pre-commit.com/> hooks, they are specified in the file `.pre-commit-config.yaml` and installed when you run `make dev_install`.
If the pre-commit configuration file is changed, remember to run `make dev_install` or `pre-commit install` again.

To manually force run the pre-commit tasks, you can type:

```bash
make pre-commit
```

## Make targets

The `Makefile` is a good resource to see how things are done.
Some of these targets include:

### Common checks before opening a PR

Includes the pre-commit hooks and running the tests with 
code coverage reports.

```bash
make check
```


### Extended checks to know more about the code

Includes security checks and other code smells.

```bash
make check-advanced
```

### Picky checks to be a code snob

Includes code complexity and documentation style checks.
```bash
make check-picky
```


### VSCode debugging

In this repo there is a `.vscode` folder with a `launch.json` file that can be used to debug the code.

You need to install the docker plugin for VSCode:

```bash
code --install-extension ms-azuretools.vscode-docker
```

You will also need to have the file `${HOME}/.aws/env` with the following content:

```
AWS_ACCESS_KEY_ID=<your access key>
AWS_SECRET_ACCESS_KEY=<your secret key>
```

Then you can debug selecting the "Run Batch pixels" configuration.

It will prompt you for the pixels function and then allow you to paste the parameters.
