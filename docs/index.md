![pixels logo](static/pixels_logo.png)

Welcome to Pixels
=================
This is the Pixels documentation.

Start with the [user guide](guide.md).

And read how to [contribute](contributing.md)


## Requirements
For the Batch docker image, the requirements are different for two reasons:

  1. Tensorflow is preinstalled on the docker image, as it has to match the
     underlying architecture on batch processing. So tensorflow does not need
     a separate install on the docker image, but it does on the dev environments.

  2. Rasterio has depends on GDAL, which comes shipped with rasterio in a binary
     format by default. In an environment where GDAL is already installed, this
     is not necessary and not even desired, as the GDAL versions might be
     different. So also here, on the Docker image, GDAL is preinstalled from apt
     and rasterio needs to be installed without binaries. Outside docker images,
     its necessary to install it with binaries.

## Batch collection explained
The pixels library has multiple levels of usage. This section describes the
batch level approach for collecting pixels data.

The [pxapi](https://github.com/tesselo/pxapi) api uses the batch mode for image
data collection. The api users have to specify the JSON configuration
parameters when creating a new collection instance.

After submitting a configuration in JSON format, the API will create jobs on
our worker backends. These workers will execute `batch.runpixels` module is run
the pixels package on worker instances.

The opening and saving of files from the storage backend on worker instances is
managed by the `pixels.stac` module. The collecting of the imagery itself is
managed by the high level `pixels.mosaic.pixel_stack` function. This function
creates a set of image slices for a set of inputs.

The `pixel_stack` function operates based on a set of input parameters, which
are loaded from a JSON configuration file in the `pixels.stac` module. This JSON
config is normally provided by users through an API.

## Configuration parameter reference
The most important definitions in the pixels configuration concern two issues:

  1. The date range that is used to collect pixels data.
  2. The way multiple source images are combined.

### Time dimension
The date range for pixels collection can either be a fixed interval in time, or
a dynamic date range.

### Fixed date range
For a fixed date range, the `start` and `end` dates will determine the time
range over which imagery is collected. Within that range, multiple slices will
be created depending on the additional configuration described below.

For the fixed date range, all items will have image slices from the same overall
date range.

### Dynamic date range
For a dynamic date range, specify the `dynamic_dates_interval` and the
`dynamic_dates_step` parameters. If these are specified, the date range will
vary for each item. The date stamp of each item will be used as the `end` date
of the collection, and the `start` date will be the `end` date minus the
dynamic date interval times the dynamic_dates_step.

The `dynamic_dates_interval` should be `months`, `weeks`, or `days`.

For instance, if the dynamic dates interval is `"weeks"` and the dynamic dates
step is `3`, then a three week interval will be used around every items date
stamp: `start = end - three weeks`.

### Image combination
The image combination is specified using the `mode` argument. Mode has four
different combination options: `all`, `latest_pixel`, `cloud_sorted_pixel`,
or `composite`.

The `all` mode will collect every image that is available for the date range
as individual slices. This will result in varying numbers of image slices for
each item.

For the `composite` mode, you can specify the method for compositing using the
`composite_method` parameter. Current choices are `SCL` and `FULL` for 
Sentinel-2, and `QA_PIXEL` for Landsat-8. `SCL` will use the SCL classification
and will stop once there are only very few cloudy pixels left. `QA_PIXEL` works
sthe same way but uses the landsat `qa_pixel` band for cloud masking. For the
`FULL` mode, the SCL classification is used as well, but all available images
are collected and the highest NDVI is used to select the best cloud free pixel
from the available images.

The `latest_pixel` mode and the `composite` mode will group images for discrete
time slices. These modes will require two additional arguments: `interval` and
`interval_step`. The `interval` defines the time step time size, and the
`interval_step` how many times that interval is used for each slice.

The `cloud_sorted_pixel` mode works the same way as the latest pixel mode, except that
it will sort the images based on cloud cover at the scene level. So this will be
the first valid pixel, in the image stack of the date range, ordered by cloud
cover.

For example, if interval is `months` and `interval_step` is `2`, one image slice
will be constructed for every two months between the `start` and `end` dates.

The `interval` should be `months`, `weeks`, or `days`.

Composite mode currently is only supported for Sentinel-2 in L2A level. There are
two different compositing methods to choose from, through the `composite_method`
argument. This argument can either be `SCL`, or `FULL`. For `SCL`, the compositing
will be incremental, the algorithm will stop once no cloudy pixels are left. The
`FULL` method will download all available scenes and use the highest NDVI value
in each cloud free pixel to decide which one to use. This tends to have much better
results in siutations where there is haze or thin clouds that are not properly
marked as clouds in the algorithm.

### Additional parameters
The satellite to use is specified in the `platforms` parameter, and the
corresponding collection level is determined using the `level` argument.

For the selected platform, the bands to collect can be specified in the `bands`
parameter.

The target resolution of the collected imagery is specified using the `scale`
parameter. The unit of the scale parameter is determined by the coordinate
reference system (CRS) or SRID of each item for which imagery is being
collected.

The `maxcloud` parameter will be used to limit the imagery that is considered to
build the time slices. This applies to every mode. For `all`, its directly
limiting the images to be registered. For the other two modes, the filter will
be used to select the imagery that can go into the latest pixel or compositing
process.

The `clip` parameter is a boolean, determining if the image slices should be
clipped against the input geometries.

The `pool_size` parameter determines how many image dates can be collected in
parallel on the backend. This is still experimental and should be used with
caution. Specifying `pool_size` to `1` is the safest option.

An alternative way of parallelizing the collections is getting all the bands in
parallel, instead of getting the dates in parallel. This can be achieved by using
the `pool_bands` boolean parameter. This can not be used in combination with date
pooling at the same time. Defaults to `False`.

The `overwrite` parameter is a boolean, determining if the images already downloaded
are overwriten. It defaults to False.


### Logging level

The default logging level is `INFO`. If you want to change this behaviour either
when using pixels as a library or from pixels API, set the environment variable
`LOG_LEVEL` to the desired one.