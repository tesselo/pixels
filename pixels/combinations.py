from pixels.const import BANDS_CORRESPONDENCE_ALL, FORMULAS


def get_index_bands(idx, satellite):
    """
    Get the appropriate bands combination for a vegetation index or a specific
    visualization according to the satellite specified.

    Parameters
    ----------
        idx : str
            The vegetation index or band combination. The str can be one of
            the following values:['infrared','rgb','swi','agriculture','geology',
            'bathymetric','ndvi','ndmi','ndwi1','ndwi2','nhi','savi','gdvi','evi','nbr',
            'bai','chlorogreen'].
        satellite : str
            The satellite platform from Landsat collection or Sentinel 2. The str or list
            must contain one or a combinations of the of the following values: 'SENTINEL_2',
            'LANDSAT_1', 'LANDSAT_2', 'LANDSAT_3', 'LANDSAT_4', 'LANDSAT_5', 'LANDSAT_7' or
            'LANDSAT_8'. If ignored, it returns values from different platforms according to
            the combination of the other parameters.
     Returns
    -------
        bands_dict : dict
            Returns dictionaries with bands names and numbers.
    """
    # Get bands names for index
    idx_list = FORMULAS["idx"]
    bands_list = FORMULAS["bands"]
    index_bands = dict(zip(idx_list, bands_list))
    bands_names = index_bands.get(idx)
    bands_dict = {}
    for band in bands_names:
        bands_dict[band] = BANDS_CORRESPONDENCE_ALL[satellite][band]
        if None in bands_dict.values():
            raise ValueError(f"The {band} band in {satellite} is empty.")
    return bands_dict
