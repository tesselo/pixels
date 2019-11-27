import requests
from pixels import const
import json
import zipfile
import io
import glob
import numpy
import os

data = json.load(open('/media/tam/rhino/work/projects/tesselo/projects/neer/neer_parcels.json'))

for geom in data:
    geom['crs'] = "EPSG:4326"
    print(geom['properties']['name'])
    # Request a weekly timestep series from March to June 2018.
    config = {
        "interval": "weeks",
        "interval_step": 1,
        "start": "2016-01-01",
        "end": "2019-07-31",
        # "start": "2017-02-01", "end": "2017-02-19",
        "geom": geom,
        "platform": const.PLATFORM_SENTINEL_2,
        "product_type": const.PRODUCT_L1C,
        "max_cloud_cover_percentage": 100,
        "clip_to_geom": True,
        "clip_all_touched": False,
        #"mode": "search_only",
        "mode": "latest_pixel",
        "color": False,
        "format": "ZIP",
        "delay": True,
        "bands": ["B04", "B08"],
        "formulas": [{"name": "ndvi", "expression": "(B08 - B04) / (B04 + B08)"}],
    }

    endpoint = "https://devpixels.tesselo.com/timeseries?key=78f300a8965e04f111e2a738a9b1cbc4f6a8bc55"
    # endpoint = "https://devpixels.tesselo.com/data?key=78f300a8965e04f111e2a738a9b1cbc4f6a8bc55"
    # endpoint = "https://pixels.tesselo.com/timeseries?key=55c836beb4fc1537de5ece6f5f40dee1b3f65036"
    # endpoint = "https://pixels.tesselo.com/data?key=55c836beb4fc1537de5ece6f5f40dee1b3f65036"
    result = requests.post(endpoint, json=config)
    result_dict = json.loads(result.content)
    print(result_dict['url'])
    # print(result_dict)

data_links = {
    'Subabul_2': 'https://devpixels.tesselo.com/timeseries/5e20070d-bd84-415b-9719-2bd8c7e0b3c7/data.zip?key=78f300a8965e04f111e2a738a9b1cbc4f6a8bc55',
    'Eucalyptus_5': 'https://devpixels.tesselo.com/timeseries/6a478506-de7a-4593-b69d-3001cdbaaab9/data.zip?key=78f300a8965e04f111e2a738a9b1cbc4f6a8bc55',
    'Eucalyptus_8': 'https://devpixels.tesselo.com/timeseries/b26396f3-34c9-4e6e-9df0-a8ba11a8c82b/data.zip?key=78f300a8965e04f111e2a738a9b1cbc4f6a8bc55',
    'Eucalyptus_2': 'https://devpixels.tesselo.com/timeseries/5b33a3d4-2119-4d6d-96eb-12ecf80588e7/data.zip?key=78f300a8965e04f111e2a738a9b1cbc4f6a8bc55',
    'Eucalyptus_1': 'https://devpixels.tesselo.com/timeseries/68ed94fc-5530-4c5e-a5c8-d2fa291bdd89/data.zip?key=78f300a8965e04f111e2a738a9b1cbc4f6a8bc55',
    'Eucalyptus_6': 'https://devpixels.tesselo.com/timeseries/0e36b870-4642-41c7-9a06-704cd823f152/data.zip?key=78f300a8965e04f111e2a738a9b1cbc4f6a8bc55',
    'Eucalyptus_7': 'https://devpixels.tesselo.com/timeseries/ef1ad865-cca9-4d58-b929-f70cb58f5fcc/data.zip?key=78f300a8965e04f111e2a738a9b1cbc4f6a8bc55',
    'Subabul_8': 'https://devpixels.tesselo.com/timeseries/0d2dcea1-1f74-46f9-98bc-dae84ce6e258/data.zip?key=78f300a8965e04f111e2a738a9b1cbc4f6a8bc55',
    'Eucalyptus_4': 'https://devpixels.tesselo.com/timeseries/750e6c6a-8f5c-4247-9b27-f8364c468a88/data.zip?key=78f300a8965e04f111e2a738a9b1cbc4f6a8bc55',
    'Eucalyptus_3': 'https://devpixels.tesselo.com/timeseries/e145731c-2ef6-4e67-a790-f0415526702f/data.zip?key=78f300a8965e04f111e2a738a9b1cbc4f6a8bc55',
    'Subabul_4': 'https://devpixels.tesselo.com/timeseries/e6777503-6cad-4cd5-9c2c-805a7aba1c63/data.zip?key=78f300a8965e04f111e2a738a9b1cbc4f6a8bc55',
    'Subabul_3': 'https://devpixels.tesselo.com/timeseries/6178aa92-dae0-4a31-b0c1-9f9e1b251bbb/data.zip?key=78f300a8965e04f111e2a738a9b1cbc4f6a8bc55',
    'Subabul_1': 'https://devpixels.tesselo.com/timeseries/a0e1d35b-f587-4d8f-9b3b-fe4f3527cea0/data.zip?key=78f300a8965e04f111e2a738a9b1cbc4f6a8bc55',
    'Subabul_5': 'https://devpixels.tesselo.com/timeseries/c9cece27-287d-4dfb-b2f5-18479a2298a3/data.zip?key=78f300a8965e04f111e2a738a9b1cbc4f6a8bc55',
    'Subabul_6': 'https://devpixels.tesselo.com/timeseries/fa36abd8-8dbc-4679-b450-449e75f35a10/data.zip?key=78f300a8965e04f111e2a738a9b1cbc4f6a8bc55',
    'Subabul_7': 'https://devpixels.tesselo.com/timeseries/86fdd329-17fd-4588-a3cf-746badf433fc/data.zip?key=78f300a8965e04f111e2a738a9b1cbc4f6a8bc55',
}

for parcel, url in data_links.items():
    r = requests.get(url)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    target = '/media/tam/rhino/work/projects/tesselo/projects/neer/data/' + parcel
    try:
        os.mkdir(target)
    except:
        pass
    z.extractall(target)

table = []
for parcel in data_links.keys():
    target = '/media/tam/rhino/work/projects/tesselo/projects/neer/data/' + parcel + '/*'
    for fl in glob.glob(target):
        start, end, flnm = fl.split('/')[-1].split('_')
        print(fl, start, end)
        if flnm == 'pixels.zip':
            with rasterio.open('zip://' + fl + '!ndvi.tif') as rst:
                pixels = rst.read()
                table.append([
                    parcel,
                    start,
                    end,
                    numpy.nanmean(pixels),
                    numpy.nanmax(pixels),
                    numpy.nanmin(pixels),
                    numpy.nanstd(pixels),
                ])
        else:
            table.append([
                    parcel,
                    start,
                    end,
                    numpy.nan,
                    numpy.nan,
                    numpy.nan,
                    numpy.nan,
            ])

table = numpy.array(table)
numpy.savetxt('/media/tam/rhino/work/projects/tesselo/projects/neer/results/ndvi.csv', table, header='parcel,start,end,mean,max,min,std', fmt='%s', comments='', delimiter=',')

import pandas
import matplotlib.pyplot as plt
df = pandas.read_csv('/media/tam/rhino/work/projects/tesselo/projects/neer/results/ndvi.csv')
df['start'] =  pandas.to_datetime(df['start'])#, format='%d%b%Y:%H:%M:%S.%f')
df['end'] =  pandas.to_datetime(df['end'])#, format='%d%b%Y:%H:%M:%S.%f')
df['species'] = df['parcel'].str[:-2]
df = df.set_index('start')
df['rolling'] = df.groupby('parcel')['mean'].rolling(2).mean().reset_index(0, drop=True)
df = df.dropna()

df[(df['species'] == 'Eucalyptus') * (df['max'] > 0.2)].dropna().groupby('parcel')['rolling'].plot()
plt.show()

plt.close('all')
counter = 0
nr_of_plots = 16
plt.figure(figsize=(9, 36))


for key, grp in df.groupby('parcel', sort=True):
    counter += 1
    # if counter != thisone:
    #     continue
    # Plot timeseries.
    ax = plt.subplot(nr_of_plots, 1, counter)
    # ax = plt.subplot(1, 1, 1)
    ax.set_title(key)
    grp = grp.sort_index()
    ax.plot(grp.index, grp['mean'])
    #ax.legend(loc='best')

plt.tight_layout()
# plt.show()

plt.savefig('/media/tam/rhino/work/projects/tesselo/projects/neer/results/ndvi_parcels.pdf')
plt.close('all')

fig, axs = plt.subplots(figsize=(16,1),
                        nrows=1, ncols=rowlength,     # fix as above
                        gridspec_kw=dict(hspace=0.4)) # Much control of gridspec

targets = zip(grouped.groups.keys(), axs.flatten())
for i, (key, ax) in enumerate(targets):
    ax.plot(grouped.get_group(key))
    ax.set_title('a=%d'%key)
ax.legend()
plt.show()
