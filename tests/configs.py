import copy
import json
import os

from pixels import const

path = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(path, 'config.json')) as fl:
    base_config = json.load(fl)


def gen_config(version):
    config = copy.deepcopy(base_config)
    config.update(version)
    return config


def gen_configs():
    versions = [
        {'formulas': [{'name': 'ndvi', 'expression': '(B08 - B04) / (B04 + B08)'}], 'bands': ['B04', 'B08']},
        {'mode': const.MODE_COMPOSITE, 'bands': const.SENTINEL_2_BANDS, 'product_type': 'S2MSI2A'},
        {'mode': const.MODE_COMPOSITE_NN, 'bands': ['SCL'] + const.SENTINEL_2_BANDS, 'product_type': 'S2MSI1C'},
        {'mode': const.MODE_COMPOSITE, 'bands': const.SENTINEL_2_BANDS, 'product_type': 'S2MSI2A'},
        {'mode': const.MODE_COMPOSITE_NN, 'bands': ['SCL'] + const.SENTINEL_2_BANDS, 'product_type': 'S2MSI1C'},
        {'format': 'PNG'},
        {'format': 'ZIP'},
        {'format': 'CSV'},
        {'bands': []},
        {'product_type': 'S2MSI2A'},
        {'platform': 'Sentinel-1', 'product_type': 'GRD', 's1_acquisition_mode': 'IW'},
        {'mode': const.MODE_COMPOSITE_NN},
        {'mode': const.MODE_COMPOSITE_INCREMENTAL_NN},
        {'target_geotransform': {'width': 112, 'height': 70, 'scale_x': 10.0, 'skew_x': 0.0, 'origin_x': -881338, 'skew_y': 0.0, 'scale_y': -10.0, 'origin_y': 5139587}},
    ]

    return [gen_config(version) for version in versions]
