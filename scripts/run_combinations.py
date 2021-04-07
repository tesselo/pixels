import pandas as pd

from pixels.combinations import get_index_bands
from pixels.const import BANDS_CORRESPONDENCE_ALL, FORMULAS

bands = pd.DataFrame.from_dict(BANDS_CORRESPONDENCE_ALL).reset_index()
bands.rename(columns={"index": "bands"}, inplace=True)
bands.head()

indexes = pd.DataFrame.from_dict(FORMULAS)
indexes.head()


# # Test get_index_bands for all combinations
# comb_list = indexes.Combination.unique().tolist()
# satellites = ["S2", "L8", "L7", "L4-L5-TM", "L4-L5-MSS", "L1-3"]
# for c in comb_list:
#     for s in satellites:
#         comb = "{}".format(c)
#         bands_dict = get_index_bands(indexes, bands, comb, s)
#         print("{}".format(c), "{}".format(s), bands_dict)

# # Test format_formula for all combinations
# comb_list = indexes.Combination.unique().tolist()
# satellites = ["S2", "L8", "L7", "L4-L5-TM", "L4-L5-MSS", "L1-3"]
# for c in comb_list:
#     for s in satellites:
#         comb = "{}".format(c)
#         bands_dict = get_index_bands(indexes, bands, comb, s)
#         formula = format_formula(indexes, bands_dict, c)
#         print("{}".format(c), "{}".format(s), formula)

# # Test NDVI
# bands_dict = get_index_bands(indexes, bands, "NDVI", "S2")
# bands_dict
# format_formula(indexes, bands_dict, "NDVI")

bands_names = get_index_bands(FORMULAS, BANDS_CORRESPONDENCE_ALL, "rgb", "SENTINEL_2")
bands_names = get_index_bands(FORMULAS, BANDS_CORRESPONDENCE_ALL, "ndvi", "SENTINEL_2")
