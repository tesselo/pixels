# User's Guide
This part of the documentation includes an overview with basic concepts,
installation instruction and topic oriented guides.

## Stac Integration

### Example for pipeline run pixel and build stac file

#### Parse training data and create stac items
Using ipython (prior set you aws credentials):
```python
from pixels.generator.stac import *

source_s3_path = 's3://tesselo-pixels-results/y_data/RePlant_v0/RePlant_tiles_clipped_tif.zip'

ycatalog = parse_data(source_s3_path, save_files=True, reference_date="2020-12-31")
```

#### Collecting and writing the pixels result
In the same ipython:
```python

config_file = 's3://tesselo-pixels-results/x_data/RePlant_v0_001/config.json'

x_collection = collect_from_catalog(ycatalog, config_file)
```

You have both X and Y stac collections you can save them as intendend.

#### Full pipeline in one function
In ipython:
```python
from pixels.generator.stac import *

source_s3_path = 's3://tesselo-pixels-results/y_data/RePlant_v0/RePlant_tiles_clipped_tif.zip'
config_file = 's3://tesselo-pixels-results/x_data/RePlant_v0_001/config.json'

final_collection = create_and_collect(source_path, config_file)
```

### Stac Browser - setting up and usage
Clone the following package:

  https://github.com/radiantearth/stac-browser

Install the package:
```
npm install
```

Create an app python file (app.py):

```python
from flask import Flask, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/<path:path_file>")

def stac(path_file):
    return send_from_directory("/path/to/folder/with_the/catalog_or_collection", path_file)

if __name__ == "__main__":
    app.run()
```

Run on one terminal:

```
python app.py
```

Open another terminal in the stac-browser folder. Run:
```
CATALOG_URL=http://127.0.0.1:5000/collection.json npm start -- --open
```

In your browser open

http://localhost:1234/


# The section below is out of date and deprecated.

## Authentication
All endpoints use Token based authentication. Pass the `?key=mysecretkey` query argument to all requests.

## Website for exploring the functionality
We created a website to interactively use the existing endpoints. On this website, you can draw a rectangle on an online map, specify the query parameters and obtain the result. It is a great way to explore the endpoint functionalities.

   https://pixels.tesselo.com

## TMS Endpoint
Latest pixel maps can be added to online maps as layers with the following url.

   https://pixels.tesselo.com/tiles/{z}/{x}/{y}.png

This endpoint has a minimal zoom level of 12, i.e. `z >= 12`. By default, this will use the latest pixel from the last 4 weeks, with a maximum cloud coverage of 20%.

The endpoint allows three customizable query parameters:

- `end` End date for the Sentinel-2 scene search, defaults to today.
- `start` Start date for the Sentinel-2 scene search, defaults to `end` minus 4 Weeks.
- `max_cloud_cover_percentage` The cloud cover percentage filter for the Sentinel-2 scene search, defaults to 20.

To customize the filters, use the endpoint as follows:

   https://pixels.tesselo.com/tiles/{z}/{x}/{y}.png?end=2018-11-04&start=2018-10-21&max_cloud_cover_percentage=10

## Image Generation Endpoint
The following endpoint allows requesting satellite image data in a flexible way. It requires a JSON configuration defining an image query.

   https://pixels.tesselo.com/data

The basic concept is that you have to specify an area of interest, a date range, and an optional filter for cloud coverage.

There are two modes:

 1. Latest pixel, which takes the latest available pixel (given time and cloud coverage filters)

 2. Comopsite, which selects the "best pixel" available (given time and cloud coverage filters)


Either POST a JSON object, or encode a JSON object string and pass the object through the `data` GET query argument.

### Configuration
In more detail, the configuration contains the following elements:

 - `geom` a GeoJSON-like feature with a polygon geometry. The bouding box of this geometry will be used as image location. The input feature requires a Coordinate Reference System (CRS) to be specified in the `crs` attribute. The structure is required to be `EPSG:X`, where `X` is a valid EPSG identifier (see example below). The CRS should either be a projected coordinate system or WGS84 (EPSG:4326). If data is passed in WGS84, the geometry is internally reprojected to the Web Mercator projection (EPSG:3857) and the scale recieved is assumed to be in that projection.
 - `scale` The pixel resolution of the output rasters. The scale needs to be in the units of the CRS of the input geometry. Defaults to 10. This parameter is ignored if `target_geotransform` is specified.
 - `end` End date for querying images, as string.
 - `start` Start date for querying images, as string.
 - `platform` The satellite platform to use. Currently only `Sentinel-2` is implemented.
 - `product_type` The processing level of the Sentinel-2 images. Either `S2MSI1C` (Level-1C) or `S2MSI2A` (Level-2A).
 - `mode` The method to stitch images together. One of ['search_only' 'latest_pixel', 'composite', 'composite_incremental', 'composite_nn', 'composite_incremental_nn'].  With `search_only` the endpoint should only send back the list of images that match the search query. This will skip the image requests and only return an image search result as json. With `latest_pixel`, the latet available pixel over the target area will be retrieved. With `composite`, the cloud free pixel with the highest NDVI will be retrieved, with `composite_incremental`, the latest cloud free pixel will be retrieved. Composite mode works only for Sentinel-2. The two modes ending in `_nn` use a neural network for cloud detection, the others use the Sen2Cor scene classification.
 - `format` A string specifying the format. One of `['PNG', 'ZIP', 'NPZ', 'CSV']`. PNG will return a rendered png image, ZIP will pack all bands as GeoTIFF files in a zip archive, NPZ will will return a compressed numpy NPZ file, and CSV will return a CSV file with point coordinates and band values. Defaults to `ZIP`
 - `color` A boolean specifying if the visual bands should be combined into an RGB file for convenience.
 - `bands` Which bands to include in the result, if a ZIP file is requested. If RGB is requested, the visual bands will be added automatically, if composite is requested, all bands will be included by default.
 - `delay` A boolean specifying if the result should be computed in asynchronous mode. If `true`, the enpdoint will return a unique link to download the data as soon as its finished. Recommended for larger areas and for ZIP, Numpy or CSV files.
 - `clip_to_geom` A boolean specifying if the output raster should be clipped against the geometry.
 - `clip_all_touched` A boolean specifying whether to include all pixels touched by the geometry while clipping. This parameter is ignored if `clip_to_geom` is `false`. Defaults to `true`.
 - `formulas` A list of formula dictionaries, each with a `name` and an `expression`. The band names in the formula needs to match available bands, so also add those to the bands list. An example formulas list is the following: `[{"name": "NDVI", "expression": "(B08 - B04) / (B08 + B04)"}, {"name": "NDWI", "expression": "(B08 - B11) / (B08 + B11)"}]`.
 - `target_geotransform` A geotransform dictionary to override the target raster configuration. By default the target raster properties will be computed from the input geometry and scale. The dictionary is expected to be of the form `{"width": 1, "height": 1, "origin_x": 0, "scale_x": 1, "skew_x": 0, "origin_y": 0, "skew_y": 0, "scale_y": -1}`. The coordinates and scale need to match the `crs` specified in the geometry.

### Example

```python
import json
import urllib
import requests

config = {
   'geom': {
       'type': 'Feature',
       'crs': 'EPSG:3857',
       'geometry': {
           'type': 'Polygon',
           'coordinates': [[
               [816091, 5946430],
               [815091, 5946430],
               [815091, 5945430],
               [816091, 5945430],
               [816091, 5946430],
           ]]
       },
   },
   'start': '2019-03-28',
   'end': '2019-04-01',
   'platform': 'Sentinel-2',
   'product_type': 'S2MSI2A',
   'max_cloud_cover_percentage': 60,
   'mode': 'latest_pixel',
   'color': True,
   'format': 'ZIP',
   'delay': True,
   'bands': ['B04', 'B03', 'B02', 'B08', 'B05'],
   'clip_to_geom': True,
   'clip_all_touched': False,
   'formulas': [{"name": "NDVI", "expression": "(B08 - B04) / (B08 + B04)"}],
}

endpoint = 'https://pixels.tesselo.com/data'
key = 'mysecretkey'
base_url = endpoint + '?key=' + key

# Using POST
requests.post(base_url, json=config)

# Using GET
config_encoded = urllib.parse.quote(json.dumps(config))
url = '{}&data={}'.format(base_url, config_encoded)
requests.get(url)
```

## WMTS endpoint
A set of predefined latest pixel maps can be viewed as an osgeo compliant [WMTS service](http://www.opengeospatial.org/standards/wmts). Use the following url as source for a WMTS layer in your favorite desktop GIS software such as QGIS or ArcGIS.

   https://pixels.tesselo.com/wmts?key=mysecretkey&max_cloud_cover_percentage=30

Authenication will be done through the `key` auth token, as with all the other endpoints. Simply include your key in the wmts url as shown in the example above. The underlying search max cloud cover percentage filter defaults to 100. If this should be more restrictive, this can be changed using the `max_cloud_cover_percentage` query parameter.

## Timeseries endpoint
An endpoint to automatically generate data for time series analysis. It iteratively calls the data endpoint using dateranges.

   https://pixels.tesselo.com/timeseries

The endpoint only accepts `POST` requests and expects that is almost identical to the configuration for the data endpoint as defined above. The only difference are two additional keywords.

The `interval` kewyord, which must be either `weeks` or `months`. The timeseries endpoint computes the corresponding timesteps between the start and end dates and calls the data endpoint. Defaults to `months`.

The `interval_step` keyword needs to be an integer, specifying how many weeks or months should be used in one step. Defaults to `1`.

The endpoint returns a download link to obtain the timeseries data in a zip file. As soon as all timesteps have been computed, the link to the combined file will return a zip file with all data from all timesteps.

The endpoint also returns a list of direct links to each individual timestep for manual tracking and processing of the individual results.

### Timeseries generation example

```python
import requests

# Request a weekly timestep series from March to June 2018.
config = {
 'interval': 'weeks',
 'interval_step': 1,
 'start': '2018-03-01',
 'end': '2018-06-30',
 ...  # All other parameters are the same as above.
}

endpoint = 'https://pixels.tesselo.com/timeseries'
key = 'mysecretkey'
base_url = endpoint + '?key=' + key

requests.post(base_url, json=config)
```

Which returns something like:

```python
{
   'message': 'Getting timeseries pixels asynchronously. Your files will be ready at the links below soon.',
   'timesteps': [
       {'end': '2018-08-08', 'start': '2018-08-01', 'url': 'https://pixels.tesselo.com/async/fad167b4-59ce-484c-9adc-ad2ccb9cbb48/93ffc1ce-4a0c-4f95-8fff-41460eeb7a39/pixels.zip?key=829c0f290b9f0f0d49fd2501e5792f8413305535'},
       {'end': '2018-08-15', 'start': '2018-08-08', 'url': 'https://pixels.tesselo.com/async/fad167b4-59ce-484c-9adc-ad2ccb9cbb48/d4a1e2a8-6433-4528-af45-73d69f50836d/pixels.zip?key=829c0f290b9f0f0d49fd2501e5792f8413305535'},
    ],
    'url': 'https://pixels.tesselo.com/timeseries/fad167b4-59ce-484c-9adc-ad2ccb9cbb48/data.zip?key=829c0f290b9f0f0d49fd2501e5792f8413305535',
}
```
## Platform and Products Detail

### Sentinel-2 Data

#### Products
Two major products are currently available, representing Top and Bottom-of-atmosphere reflectances as 16 bit integers ranging from 1-5000.  The value 0 represents "no data"

|Product Code|Type|Description|
--- | --- | --- | ---- |
|S2MSI1C|Level-1C|Top-of-atmosphere reflectances in cartographic geometry|
|S2MSI2A|Level-2A|Bottom-of-atmosphere reflectance in cartographic geometry|

#### Bands
All 13 Sentinel-2 bands are available, as well as an ESA classification accessible as 'SCL'
Bands are named using upper case B, followed by a zero-padded number, except for B8A.
Band resolutions in meters are as follows:

Name|Resolution
---|:---------:|
|B01| 60|
|B02| 10|
|B03| 10|
|B04| 10|
|B05| 20|
|B06| 20|
|B07| 20|
|B08| 10|
|B8A| 20|
|B09| 60|
|B10| 60|
|B11| 20|
|B12| 20|
|SCL| 20|

SCL Code Values (note some duplicated/ambiguous):

Code|Description
---|:---------:|
|    1|   VEGETATION|
|    2|   NOT_VEGETATED|
|    3|   WATER|
|    4|   SNOW|
|    5|   DARK_AREA_PIXELS, or CLOUD_SHADOWS, or UNCLASSIFIED|
|    6|   CLOUD_MEDIUM_PROBABILITY, or THIN_CIRRUS|
|    7|   SATURATED_OR_DEFECTIVE, or CLOUD_HIGH_PROBABILITY|
|    8|   NO_DATA|


### Sentinel-1 Data
Full ESA documentation is available here:
https://sentinel.esa.int/web/sentinel/missions/sentinel-1/data-products

Within Tesselo Pixel, the platform type is "Sentinel-1" and the product type either SLR or GRD.  Several data collection modes are also available. IW is SENTINEL-1's primary operational mode over land

#### SLC
<p>Level-1 Single Look Complex (SLC) products consist of focused SAR data geo-referenced using orbit and attitude data from the satellite and provided in zero-Doppler slant-range geometry. The products include a single look in each dimension using the full transmit signal bandwidth and consist of complex samples preserving the phase information.<p>

#### GRD
Level-1 Ground Range Detected (GRD) products consist of focused SAR data that has been detected, multi-looked and projected to ground range using an Earth ellipsoid model. Phase information is lost. The resulting product has approximately square spatial resolution pixels and square pixel spacing with reduced speckle at the cost of worse spatial resolution.
