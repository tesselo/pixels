from setuptools import find_packages, setup


def get_version():
    with open("pixels/__init__.py", "r") as init:
        for line in init.readlines():
            if line.startswith("__version__"):
                version = line.split(" = ")[1].rstrip()
                return version.split("'")[1]


with open("README.md", "r") as fh:
    long_description = fh.read()


with open("requirements.txt", "r") as fh:
    install_requires = [req.strip() for req in fh.readlines()]


setup(
    name="pixels",
    version=get_version(),
    url="https://github.com/tesselo/pixels",
    author="Daniel Wiesmann",
    author_email="daniel@tesselo.com",
    description="Pixel grabber engine",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="Copyright (c) Tesselo - Space Mosaic Lda. All rights reserved.",
    packages=find_packages(exclude=("tests", "batch", "app", "scripts")),
    include_package_data=True,
    install_requires=install_requires,
)
