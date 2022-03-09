import structlog
from dateutil.parser import parse

from pixels.config.db_config import create_db_engine_pixels, create_db_engine_pxsearch
from pixels.const import (
    BASE_LANDSAT,
    GOOGLE_URL,
    L1_L2_L3_BANDS,
    L4_L5_BANDS,
    L4_L5_BANDS_MSS,
    L7_BANDS,
    L8_BANDS,
    LANDSAT_4,
    LANDSAT_5,
    LANDSAT_7,
    LANDSAT_8,
    LANDSAT_SERIES,
    LS_BANDS_NAMES,
    LS_LOOKUP,
    S2_BANDS,
    S2_BANDS_L2A,
    S2_L1C_URL,
    S2_L2A_URL,
    SENTINEL_2,
)
from pixels.utils import compute_wgs83_bbox

logger = structlog.get_logger(__name__)

pixels_db_engine = create_db_engine_pixels()
pxsearch_db_engine = create_db_engine_pxsearch()


def search_data(
    geojson,
    start=None,
    end=None,
    platforms=None,
    maxcloud=None,
    scene=None,
    sensor=None,
    level=None,
    limit=10,
    sort="sensing_time",
):
    """
    Search for satellite images in an area of interest, for a given time interval,
    according to specificities such as the percentage of cloud cover, satellite or
    level of image processing.

    Return links to download bands for each scene resulting in the search.

    Parameters
    ----------
        geojson : dict
            The area over which the data will be selected. The geometry extent will be used
            as bounding box to select images that intersect it.
        start : str, optional
            The date to start search on pixels.
        end : str, optional
            The date to end search on pixels.
        platforms : str or list, optional
            The selection of satellites to search for images on pixels. The satellites
            can be from Landsat collection or Sentinel 2. The str or list must contain
            the following values: 'SENTINEL_2', 'LANDSAT_1', 'LANDSAT_2', 'LANDSAT_3',
            'LANDSAT_4', 'LANDSAT_5', 'LANDSAT_7' or'LANDSAT_8'. If ignored, it returns
            values from different platforms according to the combination of the other
            parameters.
        maxcloud : int, optional
            Maximun accepted cloud coverage in images. If not provided returns records with
            up to 100% cloud coverage.
        scene : str, optional
            The product id to search for a specific scene. Ignored if not provided.
        sensor: str, optional
            The imager sensor used in the Landsat 4. It can be 'MSS' or 'TM'.
        level : str, optional
            The level of image processing for Sentinel-2 satellite. It can be 'L1C'(Level-1C)
            or 'L2A'(Level-2A) that provides Bottom Of Atmosphere (BOA) reflectance images
            derived from associated Level-1C products. Ignored if platforms is not Sentinel 2.
        limit : int, optional
            Specifies the number of records to be returned in the search result.
        sort : str, optional
            Defines the ordering of the results. By default, sensing time is used, ordering
            the images from the most recent date to the oldest. Another option to order the
            results is the cloud cover which are ordered from the least cloudy to the
            cloudiest. Allowed values are "sensing_time" and "cloud_cover".
    Returns
    -------
        result : list
            List of dictionaries with characteristics of each scene present in the search
            result and the respective links to download each band.
    """

    db_result = execute_query(
        geojson, start, end, platforms, maxcloud, scene, sensor, level, limit, sort
    )

    results = [dict(row) for row in db_result]
    scenes_result = get_bands(results, level=level)

    # Convert cloud cover into float to allow json serialization of the output.
    for dat in scenes_result:
        dat["cloud_cover"] = float(dat["cloud_cover"])

    # Remove assets from final scenes_result
    if level == "L2":
        for dat in scenes_result:
            if "links" in dat:
                del dat["links"]

    # Filter real time products for landsat
    if sensor in LANDSAT_SERIES:
        scenes_result = [
            dat for dat in scenes_result if "_01_RT" not in dat["product_id"]
        ]

    logger.debug(f"Found {len(scenes_result)} in search.")

    return scenes_result


def execute_query(
    geojson, start, end, platforms, maxcloud, scene, sensor, level, limit, sort
):
    """
    Connects to the database, considering the level passed, and then executes the query.

    Parameters
    ----------
        geojson : dict
            The area over which the data will be selected. The geometry extent will be used
            as bounding box to select images that intersect it.
        start : str, optional
            The date to start search on pixels.
        end : str, optional
            The date to end search on pixels.
        platforms : str or list, optional
            The selection of satellites to search for images on pixels. The satellites
            can be from Landsat collection or Sentinel 2. The str or list must contain
            the following values: 'SENTINEL_2', 'LANDSAT_1', 'LANDSAT_2', 'LANDSAT_3',
            'LANDSAT_4', 'LANDSAT_5', 'LANDSAT_7' or'LANDSAT_8'. If ignored, it returns
            values from different platforms according to the combination of the other
            parameters.
        maxcloud : int, optional
            Maximum accepted cloud coverage in images. If not provided returns records with
            up to 100% cloud coverage.
        scene : str, optional
            The product id to search for a specific scene. Ignored if not provided.
        sensor: str, optional
            The imager sensor used in the Landsat 4. It can be 'MSS' or 'TM'.
        level : str, optional
            The level of image processing for Sentinel-2 or Landsat Collection 2.
            For the first one, it can be 'L1C'(Level-1C) or 'L2A'(Level-2A) that provides
            Bottom Of Atmosphere (BOA) reflectance images derived from associated Level-1C products.
            For Landsat the value passed must be 'L2', that includes scene-based global Level-2 surface reflectance and surface temperature science products.
            Ignored if platforms is not Sentinel 2.
        limit : int, optional
            Specifies the number of records to be returned in the search result.
        sort : str, optional
            Defines the ordering of the results. By default, sensing time is used, ordering
            the images from the most recent date to the oldest. Another option to order the
            results is the cloud cover which are ordered from the least cloudy to the
            cloudiest. Allowed values are "sensing_time" and "cloud_cover".

    Returns
    -------
        query :
            a sqlalchemy engine cursor to query execution.

    """
    query = build_query(
        start, end, platforms, maxcloud, scene, sensor, level, limit, sort
    )
    # Getting bounds.
    xmin, ymin, xmax, ymax = compute_wgs83_bbox(geojson, return_bbox=True)

    # Format and execute query.
    if level == "L2":
        formatted_query = query.format(
            xmin=xmin,
            xmax=xmax,
            ymin=ymin,
            ymax=ymax,
            schema="data",
            mgrs_tile="",
            granule_id="",
            links=", links",
        )
        engine = pxsearch_db_engine
    else:
        formatted_query = query.format(
            xmin=xmin,
            xmax=xmax,
            ymin=ymin,
            ymax=ymax,
            schema="public",
            mgrs_tile=" mgrs_tile, ",
            granule_id=" granule_id, ",
            links="",
        )
        engine = pixels_db_engine

    connection = engine.connect(close_with_result=True)
    return connection.execute(formatted_query)


def build_query(start, end, platforms, maxcloud, scene, sensor, level, limit, sort):
    """
    Format and add parameters to query template.

    Parameters
    ----------
        start : str, optional
            The date to start search on pixels.
        end : str, optional
            The date to end search on pixels.
        platforms : str or list, optional
            The selection of satellites to search for images on pixels. The satellites
            can be from Landsat collection or Sentinel 2. The str or list must contain
            the following values: 'SENTINEL_2', 'LANDSAT_1', 'LANDSAT_2', 'LANDSAT_3',
            'LANDSAT_4', 'LANDSAT_5', 'LANDSAT_7' or'LANDSAT_8'. If ignored, it returns
            values from different platforms according to the combination of the other
            parameters.
        maxcloud : int, optional
            Maximun accepted cloud coverage in images. If not provided returns records with
            up to 100% cloud coverage.
        scene : str, optional
            The product id to search for a specific scene. Ignored if not provided.
        sensor: str, optional
            The imager sensor used in the Landsat 4. It can be 'MSS' or 'TM'.
        level : str, optional
            The level of image processing for Sentinel-2 or Landsat Collection 2.
            For the first one, it can be 'L1C'(Level-1C) or 'L2A'(Level-2A) that provides
            Bottom Of Atmosphere (BOA) reflectance images derived from associated Level-1C products.
            For Landsat the value passed must be 'L2', that includes scene-based global Level-2
            surface reflectance and surface temperature science products.
            Ignored if platforms is not Sentinel 2.
        limit : int, optional
            Specifies the number of records to be returned in the search result.
        sort : str, optional
            Defines the ordering of the results. By default, sensing time is used, ordering
            the images from the most recent date to the oldest. Another option to order the
            results is the cloud cover which are ordered from the least cloudy to the
            cloudiest. Allowed values are "sensing_time" and "cloud_cover".

    Returns
    -------
        query : str
            query template to execute in postgreSQL.
    """
    # Ensure platforms follow the list format.
    if platforms is not None and not isinstance(platforms, (list, tuple)):
        platforms = [platforms]

    # SQL query template.
    query = "SELECT spacecraft_id, sensor_id, product_id, {granule_id} sensing_time, {mgrs_tile} cloud_cover, wrs_path, wrs_row, base_url {links} FROM {schema}.imagery WHERE ST_Intersects(ST_MakeEnvelope({xmin}, {ymin},{xmax},{ymax},4326), bbox)"

    # Check inputs.
    if start is not None:
        query += " AND sensing_time >= timestamp '{}' ".format(start)
    if end is not None:
        query += " AND sensing_time <= timestamp '{}' ".format(end)
    if platforms is not None:
        query += " AND spacecraft_id IN ({})".format(
            (",".join("'" + plat + "'" for plat in platforms))
        )
    if maxcloud is not None:
        query += " AND cloud_cover <= {} ".format(float(maxcloud))
    if scene is not None:
        query += " AND product_id = '{}' ".format(scene)
    if sensor is not None:
        query += " AND sensor_id = '{}' ".format(sensor)
    if is_level_valid(level, platforms):
        query += " AND granule_id LIKE '{}%'".format(level)
    if sort is not None:
        sort_order = "ASC" if sort == "cloud_cover" else "DESC"
        query += " ORDER BY {} {}".format(sort, sort_order)
    if limit is not None:
        query += " LIMIT {};".format(limit)

    return query


def get_bands(response, level):
    """
    Decides which method use to format bands and generate links to download it.

    Parameters
    ----------
        response : list
            List of dictionaries with scenes presents in the search result.
    Returns
    -------
        result : list
            List of dictionaries with scenes and bands with the respective links.
    """
    result = []
    for value in response:
        if "sentinel-2" in value["base_url"]:
            value["bands"] = format_sentinel_band(value)
        elif level == "L2":
            value["bands"] = format_ls_c2_bands(value)
        else:
            value["bands"] = format_ls_c1_band(value)

        result.append(value)

    return result


def format_sentinel_band(value):
    """
    Format base url and generate links to download sentinel bands.

    Parameters
    ----------
        value : dict
            Dictionary with characteristics of a scene (product id, sensing time, etc.).

    Returns
    -------
        data : dict
            Dictionary of each band url.
    """
    mgr = value["mgrs_tile"]
    utm_zone = mgr[:2]
    latitude_code = mgr[2:3]
    square_grid = mgr[3:5]
    date = parse(str(value["sensing_time"]))
    product_id = value["product_id"]
    sensing_time = str(date.date()).replace("-", "")
    sequence = 0
    level = value["granule_id"][:3]
    data = {}

    if level == "L2A":
        for band in S2_BANDS_L2A:
            band_template_url = "{base_url}/{utm}/{latitude}/{grid}/{year}/{month}/{product_id}_{mgr}_{sensing_time}_{sequence}_{level}/{band}.tif"
            data[band] = band_template_url.format(
                base_url=S2_L2A_URL,
                utm=utm_zone,
                latitude=latitude_code,
                grid=square_grid,
                year=date.year,
                month=date.month,
                product_id=product_id[:3],
                mgr=mgr,
                sensing_time=sensing_time,
                sequence=sequence,
                level=level,
                band=band,
            )
    else:
        for band in S2_BANDS:
            band_template_url = "{base_url}/tiles/{utm}/{latitude}/{grid}/{year}/{month}/{day}/{sequence}/{band}.jp2"
            data[band] = band_template_url.format(
                base_url=S2_L1C_URL,
                utm=utm_zone,
                latitude=latitude_code,
                grid=square_grid,
                year=date.year,
                month=date.month,
                day=date.day,
                sequence=sequence,
                band=band,
            )

    return data


def format_ls_c1_band(value):
    """
    Format base url and generate links to download landsat bands.

    Parameters
    ----------
        value : dict
            Dictionary with characteristics of a scene (product id, sensing time, etc.).

    Returns
    -------
        data : dict
            Dictionary of each band url.
    """
    plat = value["spacecraft_id"]
    product_id = value["product_id"]
    sensor = value["sensor_id"]
    data = {}
    if plat == LANDSAT_8:
        for band in L8_BANDS:
            base_url = "{}".format(value["base_url"]).replace(BASE_LANDSAT, GOOGLE_URL)
            ls_band_template = "{base_url}/{product_id}_{band}.TIF"

            data[band] = ls_band_template.format(
                base_url=base_url, product_id=product_id, band=band
            )
    elif plat == LANDSAT_7:
        for band in L7_BANDS:
            base_url = "{}".format(value["base_url"]).replace(BASE_LANDSAT, GOOGLE_URL)
            ls_band_template = "{base_url}/{product_id}_{band}.TIF"

            data[band] = ls_band_template.format(
                base_url=base_url, product_id=product_id, band=band
            )

    elif plat == LANDSAT_4 or plat == LANDSAT_5 and sensor == "TM":
        for band in L4_L5_BANDS:
            base_url = "{}".format(value["base_url"]).replace(BASE_LANDSAT, GOOGLE_URL)
            ls_band_template = "{base_url}/{product_id}_{band}.TIF"

            data[band] = ls_band_template.format(
                base_url=base_url, product_id=product_id, band=band
            )
    elif plat == LANDSAT_4 or plat == LANDSAT_5 and sensor == "MSS":
        for band in L4_L5_BANDS_MSS:
            base_url = "{}".format(value["base_url"]).replace(BASE_LANDSAT, GOOGLE_URL)
            ls_band_template = "{base_url}/{product_id}_{band}.TIF"

            data[band] = ls_band_template.format(
                base_url=base_url, product_id=product_id, band=band
            )
    else:
        for band in L1_L2_L3_BANDS:
            base_url = "{}".format(value["base_url"]).replace(BASE_LANDSAT, GOOGLE_URL)
            ls_band_template = "{base_url}/{product_id}_{band}.TIF"

            data[band] = ls_band_template.format(
                base_url=base_url, product_id=product_id, band=band
            )
    return data


def is_level_valid(level, platforms):
    """
    Checks whether the use of the Level parameter is valid.

    Parameters
    ----------
        level : str
            Image processing level for Sentinel 2.
        platforms : list or tuple
            The selection of satellites to search for images on pixels.
    Returns
    -------
        True if the level is not empty, the platform is a unique value list and contains
        Sentinel 2.
    """
    return level is not None and len(platforms) == 1 and platforms[0] == SENTINEL_2


def format_ls_c2_bands(value):
    """
        Get  links to download landsat collection 02 bands. from assets data.

    Parameters
    ----------
        value : dict
            Dictionary with characteristics of a scene (product id, sensing time, assets, etc.).

    Returns
    -------
        bands_links : dict
            Dictionary of each band url.
    """

    bands_links = {}

    links = value["links"]
    for band_name, band_data in links.items():
        if band_name in LS_BANDS_NAMES:
            bands_links[LS_LOOKUP[band_name]] = band_data["alternate"]["s3"]["href"]

    return bands_links
