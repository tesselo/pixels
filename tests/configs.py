import copy
import json
import os

path = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(path, 'config.json')) as fl:
    base_config = json.load(fl)


def gen_config(version):
    config = copy.deepcopy(base_config)
    config.update(version)
    return config


def gen_configs():
    versions = [
        {'format': 'PNG'},
        {'format': 'ZIP'},
        {'format': 'CSV'},
        {'composite': True, 'latest_pixel': False},
        {'bands': None},
        {'product_type': 'S2MSI2A'},
    ]

    return [gen_config(version) for version in versions]
