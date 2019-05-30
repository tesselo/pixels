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
        {'mode': 'composite', 'product_type': 'S2MSI2A'},
        {'mode': 'composite_incremental', 'bands': ['SCL', 'B03'], 'product_type': 'S2MSI2A'},
        {'format': 'PNG'},
        {'format': 'ZIP'},
        {'format': 'CSV'},
        {'bands': None},
        {'product_type': 'S2MSI2A'},
        {'platform': 'Sentinel-1', 'product_type': 'GRD', 's1_acquisition_mode': 'IW'},
    ]

    return [gen_config(version) for version in versions]
