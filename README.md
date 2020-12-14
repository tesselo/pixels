# Pixels
A globel pixel grabber engine.

With a simple [documentation](docs/index.md).

Copyright 2020 Tesselo - Space Mosaic Lda. All rights reserved.

## Environment
For batch jobs `AWS_S3_BUCKET` and `PIXELS_PROJECT_ID`.

## Run tests
Pip install pytests, then run
```
pytest tests
```

## Deployment
Deployment needs to be done through virtualenvs that have the minimal number of
libraries installed to have slim lambda packages.

```shell
# Remove pyc files before deployment.
find ./ -name "*.pyc" -exec rm -f {} \;
```

```shell
# Deploy dev.
workon pixels-deploy-dev
./deploy.sh dev
```

```shell
# Deploy production.
workon pixels-deploy-production
./deploy.sh production
```

## Config
This is still under construction, but should represent all the options one can
specify when running pixels.
```json
{
  "min_date": "1972-07-23",
  "max_date": "2020-11-17",
  "scale": 9.5546,
  "interval": ["scenes", "weeks", "months"],
  "intervals_per_step": 1,
  "scene_limit_per_step": 10,
  "bands": ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B10", "B11", "B12"],
  "collection": ["Sentinel-2-l2a", "Sentinel-2-l1c", "Landsat"],
  "clip": false,
  "max_cloud_cover": 10,
  "training_geofile": "landcover_samples.gpkg",
  "keras_model_definition": "model.json",
  "keras_model_input_shape": ["1D", "2D"],
  "prediction_geofile": "study_area.gpkg",
  "prediction_tile_index": ["CanadianNAD83_LCC", "EuropeanETRS89_LAEAQuad", "LINZAntarticaMapTilegrid", "NZTM2000", "UPSAntarcticWGS84Quad", "UPSArcticWGS84Quad", "UTM31WGS84Quad", "WebMercatorQuad", "WorldCRS84Quad", "WorldMercatorWGS84Quad"],
}
```
