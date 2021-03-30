import pandas as pd
import re

# Dataframe with band name and satellite equivallents 
bands = pd.read_csv('/home/keren/projects/API_Images/satellites.csv')
bands

bands.Bands.unique()

# Dataframe with indexes and formulas
indexes = pd.read_csv('/home/keren/projects/API_Images/combinations.csv')
indexes

indexes.columns

# Map df indexes using  df bands    
def get_index_bands(index_df, band_df, combination, satellite):
    
    combination = combination
    
    # Get bands names for index
    bands_names = index_df[index_df['Combination'] == combination]['Bands']   # Return series.
    bands_names = str(bands_names).split()[1].split(',')    # Convert to str.
    #print(bands_names)
    
    # Returns bands numbers according to the names  bands and the specified satellite.
    bands_dict = {}
    for name in bands_names:
        #print(f" {name}") # format
        bands = band_df[band_df['Bands'] == name][satellite] #return each row 3 series -> each band
        bands = str(bands).split()[1].split(',')[0]
        print(bands)
        if bands == '0':
            raise ValueError(f'{name} band in {satellite} is empty')
    # Convert result into a dict where key is the name of band and value the properly band
        bands_dict[name]=bands
    return bands_dict

#Test some examples for empty band case = L1-3
#bands_dict = get_bands(indexes, bands, 'RGB', 'L1-3')
#bands_dict = get_bands(indexes, bands, 'Bathymetric', 'L7')
bands_dict = get_bands(indexes, bands, 'NBR', 'L4-L5-MSS')
bands_dict

# Function to format formula using correct bands
def format_formula(df, bands_dict, combination):
    
    combination = combination
    comb_list = ['Infrared', 'RGB', 'SWI', 'Agriculture','Geology', 'Bathymetric']
    
    # If formula -Ok
    if combination not in comb_list:
        formula = df[df['Combination'] == combination]['Formula']   # Return series.
        #print(formula)
        formula = str(formula).split()[1].split(',')[0]   # pick first str in lits and convert to str
        #print("Index: ", formula)
        
        # Format formula using dict values
        for key, value in bands_dict.items():
            #print(key, value)
            formula = formula.replace(key, value)
            
    # If only visualization -OK
    else:
        formula = df[df['Combination'] == combination]['Formula']   # Return series.
        formula = str(formula).split()[1].split(',') # Convert to list of str
        #print("Visualization: ", formula)
    
        # Format formula using dict values
        formula = [bands_dict.get(item,item) for item in formula]
    
    return formula

# Test get_bands for all combinations
comb_list = indexes.Combination.unique().tolist()
satellites = ['S2', 'L8', 'L7', 'L4-L5-TM', 'L4-L5-MSS', 'L1-3']
for c in comb_list:
    for s in satellites:
        comb = '{}'.format(c)
        bands_dict = get_bands(indexes, bands, comb, s)
        print('{}'.format(c),'{}'.format(s), bands_dict)

# Test format_formula for all combinations
comb_list = indexes.Combination.unique().tolist()
for c in comb_list:
    comb = '{}'.format(c)
    bands_dict = get_bands(indexes, bands, comb, 'S2')
    formula = format_formula(indexes, bands_dict, c)
    print('{}'.format(c), formula)

#Test NDVI
bands_dict = get_bands(indexes, bands, 'NDVI', 'S2')
bands_dict
#format_formula(indexes, bands_dict, 'NDVI')

# Funciona matematicamente?
# L1-3 e L4-5 MSS não tem banda azul
# raise error for satellites that dont have a band needed for an index like coastal, blue or vre