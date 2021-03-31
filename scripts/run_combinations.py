from pixels.combinations import get_index_bands, format_formula
from pixels.search import search_data

#Test some examples for empty band case = L1-3
bands_dict = get_index_bands(indexes, bands, 'RGB', 'L1-3')
bands_dict = get_index_bands(indexes, bands, 'Bathymetric', 'L7')
bands_dict = get_index_bands(indexes, bands, 'NBR', 'L4-L5-MSS')
bands_dict

# Test get_index_bands for all combinations
comb_list = indexes.Combination.unique().tolist()
satellites = ['S2', 'L8', 'L7', 'L4-L5-TM', 'L4-L5-MSS', 'L1-3']
for c in comb_list:
    for s in satellites:
        comb = '{}'.format(c)
        bands_dict = get_index_bands(indexes, bands, comb, s)
        print('{}'.format(c),'{}'.format(s), bands_dict)

# Test format_formula for all combinations
comb_list = indexes.Combination.unique().tolist()
satellites = ['S2', 'L8', 'L7', 'L4-L5-TM', 'L4-L5-MSS', 'L1-3']
for c in comb_list:
    for s in satellites:
        comb = '{}'.format(c)
        bands_dict = get_index_bands(indexes, bands, comb, s)
        formula = format_formula(indexes, bands_dict, c)
        print('{}'.format(c), '{}'.format(s), formula)

#Test NDVI
bands_dict = get_index_bands(indexes, bands, 'NDVI', 'S2')
bands_dict
format_formula(indexes, bands_dict, 'NDVI')