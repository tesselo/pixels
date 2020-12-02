import logging
import os

import sqlalchemy
from dateutil.parser import parse

from pixels.const import AWS_URL, BASE_LANDSAT, GOOGLE_URL, LS_BANDS, S2_BANDS
from pixels.utils import compute_wgs83_bbox

logger = logging.getLogger(__name__)

DB_NAME = os.environ.get("DB_NAME", "pixels")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_USER = os.environ.get("DB_USER", "postgres")

# Setup db engine and connect.
DB_TEMPLATE = "postgresql+pg8000://{username}:{password}@{host}:{port}/{database}"
db_url = DB_TEMPLATE.format(
    username=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=5432, database=DB_NAME
)
engine = sqlalchemy.create_engine(db_url, client_encoding="utf8")
connection = engine.connect()


def search_data(
    geojson,
    start=None,
    end=None,
    platforms=None,
    maxcloud=None,
    scene=None,
    limit=10,
    sort="sensing_time",
):
    """
    Query data from the eo_catalog DB
    """
    # Getting bounds
    xmin, ymin, xmax, ymax = compute_wgs83_bbox(geojson, return_bbox=True)

    # SQL query template
    query = "SELECT product_id, sensing_time, mgrs_tile, cloud_cover, base_url FROM imagery WHERE ST_Intersects(ST_MakeEnvelope({xmin}, {ymin},{xmax},{ymax},4326),bbox)"

    # Check inputs
    if start is not None:
        query += " AND sensing_time >= timestamp '{}' ".format(start)
    if end is not None:
        query += " AND sensing_time <= timestamp '{}' ".format(end)
    if platforms is not None:
        query += " AND spacecraft_id IN ({})".format(
            (",".join("'" + plat + "'" for plat in platforms))
        )
    if maxcloud is not None:
        query += " AND cloud_cover <= {} ".format(maxcloud)
    if scene is not None:
        query += " AND product_id = '{}' ".format(scene)
    if sort is not None:
        query += " ORDER BY {} DESC".format(sort)
    if limit is not None:
        query += " LIMIT {};".format(limit)

    # Execute and format querry
    formatted_query = query.format(xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax)
    result = engine.execute(formatted_query)
    # Transform ResultProxy into json
    result = get_bands([dict(row) for row in result])
    # Convert cloud cover into float to allow json serialization of the output.
    for dat in result:
        dat["cloud_cover"] = float(dat["cloud_cover"])

    logger.debug("Found {} results in search.".format(len(result)))

    return result


def get_bands(response):
    result = []
    for value in response:
        if "sentinel-2" in value["base_url"]:
            value["bands"] = format_sentinel_band(value)
        else:
            value["bands"] = format_ls_band(value)

        result.append(value)

    return result


def format_sentinel_band(value):

    mgr = value["mgrs_tile"]
    utm_zone = mgr[:2]
    latitude_code = mgr[2:3]
    square_grid = mgr[3:5]
    base_url = AWS_URL
    date = parse(str(value["sensing_time"]))
    product_id = value["product_id"]
    sensing_time = str(date.date()).replace("-", "")
    sequence = 0
    level = "L2A"
    data = {}

    for band in S2_BANDS:
        band_template_url = "{base_url}/{utm}/{latitude}/{square_grid}/{year}/{month}/{product_id}_{mgr}_{sensing_time}_{sequence}_{level}/{band}.tif"
        data[band] = band_template_url.format(
            base_url=base_url,
            utm=utm_zone,
            latitude=latitude_code,
            square_grid=square_grid,
            year=date.year,
            month=date.month,
            product_id=product_id[:3],
            mgr=mgr,
            sensing_time=sensing_time,
            sequence=sequence,
            level=level,
            band=band,
        )

    return data


def format_ls_band(value):

    product_id = value["product_id"]
    data = {}
    for band in LS_BANDS:

        base_url = "{}".format(value["base_url"]).replace(BASE_LANDSAT, GOOGLE_URL)
        ls_band_template = "{base_url}/{product_id}_{band}.TIF"

        data[band] = ls_band_template.format(
            base_url=base_url, product_id=product_id, band=band
        )

    return data
