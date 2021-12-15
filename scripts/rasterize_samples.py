import os

import click
import geopandas as gpd
import rasterio
from dateutil import parser
from rasterio.features import rasterize

from pixels.utils import compute_transform


@click.command()
@click.option(
    "--source",
    help="Vector layer to rasterize",
    required=True,
    type=click.Path(exists=True),
)
@click.option(
    "--sample_column", help="Attribute column name for sample value", required=True
)
@click.option("--scale", help="Target pixel size", required=True, type=click.INT)
@click.option(
    "--output_dir",
    help="Directory to write raster files",
    required=True,
    type=click.Path(exists=True),
)
@click.option(
    "--srid", default=None, help="Target projection EPSG srid", type=click.INT
)
@click.option("--nodata", default=None, help="Target nodata value", type=click.INT)
@click.option(
    "--date_column",
    default=None,
    help="Attribute column name for sample date that will be written into metadata tag",
)
@click.option("--dtype", default="uint8", help="Target datatype of output rasters")
@click.option(
    "--all_touched", default=False, help="Rasterization parameter", type=click.BOOL
)
def rasterize_samples(
    source,
    sample_column,
    scale,
    output_dir,
    srid,
    nodata,
    date_column,
    dtype,
    all_touched,
):
    """Rasterize all samples from a vector layer."""
    # Open vector layer and ensure desired projection.
    data = gpd.read_file(source)
    if srid:
        data = data.to_crs(epsg=srid)

    if sample_column not in data.columns:
        raise ValueError(
            f"Sample column {sample_column} not found. Options are {data.columns}"
        )
    if date_column and date_column not in data.columns:
        raise ValueError(
            f"Date column {date_column} not found. Options are {data.columns}"
        )

    for index, row in data.iterrows():
        # Get class digital number from feature.
        sample_value = row.get(sample_column)
        if date_column:
            sample_date = parser.parse(row.get(date_column)).date()
        # Compute target raster definition.
        transform, width, height = compute_transform(row.geometry, scale)
        # Ensure minimum of one pixel for small samples.
        if width == 0:
            width = 1
        if height == 0:
            height = 1
        mask = rasterize(
            [row.geometry],
            out_shape=(height, width),
            transform=transform,
            all_touched=all_touched,
            fill=nodata,
            default_value=sample_value,
        ).astype(dtype)
        # Copy metadata from geom raster.
        dest_filename = f"sample_{index}.tif"
        destination = os.path.join(output_dir, dest_filename)
        creation_args = {
            "driver": "GTiff",
            "nodata": nodata,
            "width": width,
            "height": height,
            "count": 1,
            "crs": "EPSG:{}".format(srid),
            "transform": transform,
            "dtype": dtype,
            "compress": "deflate",
        }
        with rasterio.open(destination, "w", **creation_args) as dst:
            dst.write(mask, 1)
            if sample_date:
                dst.update_tags(datetime=str(sample_date))
        if index % 100 == 0:
            print(f"Processed {index}/{len(data)} geometries.")


if __name__ == "__main__":
    rasterize_samples()
