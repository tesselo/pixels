import numpy
from rasterio.io import MemoryFile


def warp_from_s3(bucket, prefix, transform, width, height, crs):
    # Prepare creation parameters for memory raster.
    dtype = "uint8" if "SCL" in prefix else "uint16"
    creation_args = {
        "driver": "GTiff",
        "dtype": dtype,
        "nodata": 0,
        "count": 1,
        "crs": crs,
        "transform": transform,
        "width": width,
        "height": height,
    }
    # Open memory destination file.
    memfile = MemoryFile()
    with memfile.open(**creation_args) as rst:
        if "SCL" in prefix:
            fake_data = numpy.random.random((1, height, width)) * 12
        else:
            fake_data = numpy.random.random((1, height, width)) * 1e4
        rst.write(fake_data.astype(dtype))
    # Return memfile.
    memfile.seek(0)
    return memfile


def search(*args, **kwargs):
    return [
        {
            "prefix": "tiles/29/T/NG/2019/3/31/0/",
            "mgrs": "29TNG",
            "processing_level": "Level-1C",
            "platform_name": "Sentinel-2",
            "max_cloud_cover_percentage": "24.6693",
            "date": "2019-03-31 11:21:19.024000+00:00",
            "footprint": "SRID=4326;MULTIPOLYGON (((-7.6855774 41.45624189757688, -7.6651 42.44491772432881, -8.832275 42.451713278350944, -8.860779 42.362461714776536, -8.907379 42.2153754989327, -8.954041 42.06841215450682, -9.000244 41.92163464909506, -9.000244 41.463751887157464, -7.6855774 41.45624189757688)))",
        },
        {
            "prefix": "tiles/29/T/NG/2019/3/29/0/",
            "mgrs": "29TNG",
            "processing_level": "Level-1C",
            "platform_name": "Sentinel-2",
            "max_cloud_cover_percentage": "0.4506",
            "date": "2019-03-29 11:33:21.024000+00:00",
            "footprint": "SRID=4326;MULTIPOLYGON (((-8.020477 41.458155019581305, -7.994049 41.52938842569611, -7.9406433 41.675905179396494, -7.8866577 41.8222422905784, -7.831848 41.96830841491614, -7.7761536 42.114150455781285, -7.7206116 42.260086313583926, -7.6659546 42.40360124288032, -7.6651 42.44491772432881, -9.000244 42.45269119915018, -9.000244 41.463751887157464, -8.020477 41.458155019581305)))",
        },
        {
            "prefix": "tiles/29/T/NG/2019/3/26/0/",
            "mgrs": "29TNG",
            "processing_level": "Level-1C",
            "platform_name": "Sentinel-2",
            "max_cloud_cover_percentage": "0.0",
            "date": "2019-03-26 11:21:11.024000+00:00",
            "footprint": "SRID=4326;MULTIPOLYGON (((-7.6855774 41.45624189757688, -7.6651 42.44491772432881, -8.82959 42.45169759199916, -8.86908 42.327066376158704, -8.915497 42.18012494954698, -8.961761 42.03310334906611, -9.000244 41.91063415620386, -9.000244 41.463751887157464, -7.6855774 41.45624189757688)))",
        },
    ]
