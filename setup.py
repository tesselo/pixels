from setuptools import find_packages, setup


def get_version():
    with open('pixels/__init__.py', 'r') as init:
        for line in init.readlines():
            if line.startswith('__version__'):
                version = line.split(' = ')[1].rstrip()
                return version.split("'")[1]


with open("README.md", "r") as fh:
    long_description = fh.read()


setup(
    name='pixels',
    version=get_version(),
    url='https://github.com/tesselo/pixels',
    author='Daniel Wiesmann',
    author_email='daniel@tesselo.com',
    description='Pixel grabber engine',
    long_description=long_description,
    long_description_content_type="text/markdown",
    license='Copyright (c) Tesselo - Space Mosaic Lda.',
    packages=find_packages(exclude=('tests', 'batch', 'app', 'scripts')),
    include_package_data=True,
    install_requires=[
        'numpy>=1.18.5',
        'rasterio>=1.1.8',
        'requests>=2.22.0'
        'fiona>=1.8.17'
    ],
)
