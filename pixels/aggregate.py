import io

import numpy
import rasterio
from rasterio import Affine
from rasterio.io import MemoryFile
from rasterio.warp import Resampling, reproject

from pixels import utils

scale = utils.tile_scale(14)
tbounds = utils.tile_bounds(14, 4562, 6532)

trf = {
    'width': 256,
    'height': 256,
    'scale_x': scale,
    'skew_x': 0.0,
    'origin_x': tbounds[0],
    'skew_y': 0.0,
    'scale_y': -scale,
    'origin_y': tbounds[3],
}
transform = Affine(trf['scale_x'], trf['skew_x'], trf['origin_x'], trf['skew_y'], trf['scale_y'], trf['origin_y'])
width = trf['width']
height = trf['height']
crs = 'epsg:3857'

# Setup XML file for opening composite as TMS layer.
fl = io.BytesIO(b"""<GDAL_WMS>
<Service name="TMS">
    <ImageFormat>image/tiff</ImageFormat>
    <ServerUrl>{host}/composite/{project_id}/${{z}}/${{x}}/${{y}}.tif?key=829c0f290b9f0f0d49fd2501e5792f8413305535&amp;formula={formula}</ServerUrl>
    <SRS>EPSG:3857</SRS>
</Service>
<DataWindow>
    <UpperLeftX>-20037508.34</UpperLeftX>
    <UpperLeftY>20037508.34</UpperLeftY>
    <LowerRightX>20037508.34</LowerRightX>
    <LowerRightY>-20037508.34</LowerRightY>
    <TileLevel>14</TileLevel>
    <TileCountX>1</TileCountX>
    <TileCountY>1</TileCountY>
    <YOrigin>top</YOrigin>
</DataWindow>
<DataType>Float64</DataType>
<Projection>EPSG:3857</Projection>
<BlockSizeX>256</BlockSizeX>
<BlockSizeY>256</BlockSizeY>
<BandsCount>1</BandsCount>
</GDAL_WMS>
""".format(
    host='http://127.0.0.1:5000',
    project_id='florence-s2',
    formula='(B08-B04)/(B08%2BB04)'),
)

# Open WMS service xml.
with rasterio.open(fl, driver='WMS') as src:
    print(src.meta)

    creation_args = src.meta.copy()
    creation_args.update({
        'driver': 'GTiff',
        'crs': crs,
        'transform': transform,
        'width': width,
        'height': height,
        'dtype': 'float64',
    })
    # Prepare projection arguments.
    proj_args = {
        'dst_transform': transform,
        'dst_crs': crs,
        'resampling': Resampling.cubic,
        'src_crs': src.crs,
    }
    # Get raster algebra from api destination.
    memfile = MemoryFile()
    with memfile.open(**creation_args) as dst:
        for i in range(1, src.count + 1):
            proj_args.update({
                'source': rasterio.band(src, i),
                'destination': rasterio.band(dst, i),
            })
            reproject(**proj_args)
    memfile.seek(0)

    # Clip pixels to geom.
    clipped = utils.clip_to_geom({'index': memfile}, geom)

    # Open pixels as array.
    with clipped.open() as clrst:
        data = clrst.read().ravel()

    # Compute index stats from pixels.
    stats = {
        'min': numpy.min(data),
        'max': numpy.max(data),
        'avg': numpy.average(data),
        'std': numpy.std(data),
        't0': len(data),
        't1': numpy.sum(data),
        't2': numpy.sum(numpy.square(data)),
    }
