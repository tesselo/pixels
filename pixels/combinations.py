import pandas as pd

from pixels.const import BANDS_CORRESPONDENCE_ALL, FORMULAS

bands = pd.DataFrame.from_dict(BANDS_CORRESPONDENCE_ALL).reset_index()
bands.rename(columns={"index": "bands"}, inplace=True)
bands.head()

indexes = pd.DataFrame.from_dict(FORMULAS)
indexes.head()

# Add docstrings
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
            The satellite platform.
     Returns
    -------
        bands_dict : dict
            Returns dictionaries with bands names and numbers.
    """
    # Get bands names for index
    idx_list = list(FORMULAS.values())[0]
    bands_list = list(FORMULAS.values())[2]
    index_bands = dict(zip(idx_list, bands_list))
    bands_names = index_bands.get(idx)
    bands_dict = {}
    for band in bands_names:
        bands_dict[band] = BANDS_CORRESPONDENCE_ALL[satellite][band]
        if None in bands_dict.values():
            raise ValueError(f"The {band} band in {satellite} is empty.")
    return bands_dict
