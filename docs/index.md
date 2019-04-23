# Pixels

A global pixel grabber engine.

## Documentation

### Authentication
All endpoints use Token based authentication. Pass the `?key=mysecretkey` query argument to all requests.

### Website for exploring the functionality
We created a website to interactively use the existing endpoints. On this website, you can draw a rectangle on an online map, specify the query parameters and obtain the result. It is a great way to explore the endpoint functionalities.

    https://pixels.tesselo.com

### TMS Endpoint
Latest pixel maps can be added to online maps as layers with the following url.

    https://pixels.tesselo.com/tiles/{z}/{x}/{y}.png

This endpoint has a minimal zoom level of 12, i.e. `z >= 12`. By default, this will use the latest pixel from the last 4 weeks, with a maximum cloud coverage of 20%.

The endpoint allows three customizable query parameters:

- `end` End date for the Sentinel-2 scene search, defaults to today.
- `start` Start date for the Sentinel-2 scene search, defaults to `end` minus 4 Weeks.
- `max_cloud_cover_percentage` The cloud cover percentage filter for the Sentinel-2 scene search, defaults to 20.

To customize the filters, use the endpoint as follows:

    https://pixels.tesselo.com/tiles/{z}/{x}/{y}.png?end=2018-11-04&start=2018-10-21&max_cloud_cover_percentage=10

### Image generation enpdoint
The following endpoint allows requesting satellite image data in a flexible way. It requires a JSON configuration defining an image query.

    https://pixels.tesselo.com/data

The basic concept is that you have to specify an area of interest, a date range, and an optional filter for cloud coverage.

There are two modes:

  1. Latest pixel, which takes the latest available pixel (given time and cloud coverage filters)

  2. Comopsite, which selects the "best pixel" available (given time and cloud coverage filters)


Either POST a JSON object, or encode a JSON object string and pass the object through the `data` GET query argument.

#### Configuration
In more detail, the configuration contains the following elements:

  - `geom` a GeoJSON feature with a polygon geometry. The bouding box of this geometry will be used as image location. The input can be in any projection but web mercator (EPSG:3557) is recommended.
  - `end` End date for querying images, as string.
  - `start` Start date for querying images, as string.
  - `platform` The satellite platform to use. Currently only `Sentinel-2` is implemented.
  - `product_type` The processing level of the Sentinel-2 images. Either `S2MSI1C` (Level-1C) or `S2MSI2A` (Level-2A).
  - `composite` A boolean switching on composite mode
  - `latest_pixel` A boolean switching on latest pixel mode.
  - `format` A string specifying the format. One of `['PNG', 'ZIP', 'NPZ']`. PNG will return a rendered png image, ZIP will pack all bands as GeoTIFF files in a zip archive, NPZ will will return a compressed numpy NPZ file. Defaults to `ZIP`
  - `color` A boolean specifying if the visual bands should be combined into an RGB file for convenience.
  - `bands` Which bands to include in the result, if a ZIP file is requested. If RGB is requested, the visual bands will be added automatically, if composite is requested, all bands will be included by default.
  - `delay` A boolean specifying if the result should be computed in asynchronous mode. If `true`, the enpdoint will return a unique link to download the data as soon as its finished. Recommended for larger areas and for ZIP files (with render=False).
  - `search_only` A boolean specifying if the endpoint should only send back the list of images that match the search query. This will skip the image requests and only return an image search result as json.
  - `clip_to_geom` A boolean specifying if the output raster should be clipped against the geometry.

#### Example

```python
import json
import urllib
import requests

data = {
    "geom": {
        "type": "Feature",
        "srs": "EPSG:3857",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [816091, 5946430],
                [815091, 5946430],
                [815091, 5945430],
                [816091, 5945430],
                [816091, 5946430],
            ]]
        },
    },
    "start": "2019-03-28",
    "end": "2019-04-01",
    "platform": "Sentinel-2",
    "product_type": "S2MSI2A",
    "s2_max_cloud_cover_percentage": 60,
    "search_only": False,
    "composite": True,
    "latest_pixel": False,
    "color": True,
    "format": "ZIP",
    "delay": True,
    "bands": ["B04", "B03", "B02", "B08", "B05"],
}

endpoint = 'https://pixels.tesselo.com/data'
key = 'mysecretkey'
base_url = endpoint + '?key=' + key

# Using POST
requests.post(base_url, json=data)

# Using GET
data_encoded = urllib.parse.quote(json.dumps(data))
url = '{}&data={}'.format(base_url, data_encoded)
requests.get(url)
```
