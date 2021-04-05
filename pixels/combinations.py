import pandas as pd

from pixels.const import BANDS_CORRESPONDENCE_ALL, FORMULAS

bands = pd.DataFrame.from_dict(BANDS_CORRESPONDENCE_ALL).reset_index()
bands.rename(columns={"index": "bands"}, inplace=True)
bands.head()

indexes = pd.DataFrame.from_dict(FORMULAS)
indexes.head()


# Map df indexes using  df bands
def get_idx_bands(index_df, band_df, idx, satellite):
    idx = idx
    # Get bands names for index
    bands_names = index_df[index_df["idx"] == idx]["bands"]  # Return series.
    bands_names = str(bands_names).split()[1].split(",")  # Convert to str.

    # Returns bands numbers according to the names  bands to the specified satellite.
    bands_dict = {}
    for name in bands_names:
        # print(f" {name}")
        bands = band_df[band_df["bands"] == name][
            satellite
        ]  # Return each row as a series -> each band
        bands = str(bands).split()[1].split(",")[0]
        print(bands)
        #     # if bands == '0':
        #     # raise ValueError(f'{name} band in {satellite} is empty')
        # Convert result into a dict where key is the name of band and value the properly band.
        bands_dict[name] = bands
    return bands_dict


# Method to format formula using correct bands
def format_formula(df, bands_dict, combination):

    combination = combination
    comb_list = ["Infrared", "RGB", "SWI", "Agriculture", "Geology", "Bathymetric"]

    # If formula -Ok
    if combination not in comb_list:
        formula = df[df["Combination"] == combination]["Formula"]  # Return series.
        # print(formula)
        formula = (
            str(formula).split()[1].split(",")[0]
        )  # pick first str in lits and convert to str
        # print("Index: ", formula)

        # Format formula using dict values
        for key, value in bands_dict.items():
            # print(key, value)
            formula = formula.replace(key, value)

    # If only visualization -OK
    else:
        formula = df[df["Combination"] == combination]["Formula"]  # Return series.
        formula = str(formula).split()[1].split(",")  # Convert to list of str
        # print("Visualization: ", formula)

        # Format formula using dict values
        formula = [bands_dict.get(item, item) for item in formula]

    return formula
