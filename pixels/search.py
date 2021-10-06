import os

import structlog
from dateutil.parser import parse
from datetime import datetime, timedelta
from sqlalchemy import create_engine

from pixels.const import (
    S2_L1C_URL,
    S2_L2A_URL,
    LS_L2_URL,
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
    S2_BANDS,
    S2_BANDS_L2A,
    SENTINEL_2,
    L8_COG_ITEMS,
    L7_COG_ITEMS,
    L4_L5_COG_ITEMS
)
from pixels.utils import compute_wgs83_bbox

logger = structlog.get_logger(__name__)

DB_NAME = os.getenv("DB_NAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")

# Setup db engine and connect.
if DB_NAME is not None:
    DB_TEMPLATE = "postgresql+pg8000://{username}:{password}@{host}:{port}/{database}"
    db_url = DB_TEMPLATE.format(
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=5432,
        database=DB_NAME,
    )
    engine = create_engine(db_url, client_encoding="utf8")
else:
    engine = create_engine(
        "postgresql+pg8000://postgres:postgres@localhost:5432/pixels"
    )


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
    level of image processing. Returns links to download bands for each scene
    resulting in the search.

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
            cloudiest. Allowed valeus are "sensing_time" and "cloud_cover".
    Returns
    -------
        result : list
            List of dictionaries with characteristics of each scene present in the search
            result and the respective links to download each band.
    """
    # Convert str in list.
    if platforms is not None and not isinstance(platforms, (list, tuple)):
        platforms = [platforms]

    # Getting bounds.
    xmin, ymin, xmax, ymax = compute_wgs83_bbox(geojson, return_bbox=True)

    # SQL query template.
    query = "SELECT spacecraft_id, sensor_id, product_id, granule_id, sensing_time, mgrs_tile, cloud_cover, wrs_path, wrs_row, base_url FROM imagery WHERE ST_Intersects(ST_MakeEnvelope({xmin}, {ymin},{xmax},{ymax},4326),bbox)"

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
        query += " AND cloud_cover <= {} ".format(maxcloud)
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

    # Execute and format querry.
    formatted_query = query.format(xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax)
    result = engine.execute(formatted_query)
    # Transform ResultProxy into json.
    result = get_bands([dict(row) for row in result])
    # Convert cloud cover into float to allow json serialization of the output.
    for dat in result:
        dat["cloud_cover"] = float(dat["cloud_cover"])

    logger.debug("Found {} results in search.".format(len(result)))

    return result


def get_bands(response):
    """
    Decides which method use to format bands and generate links to download it.

    Parameters
    ----------
        response : list
            List of dictionaries with scenes presents in the search result.
    Returns
    -------
        result : list
            List of dictionaries with scenes and bands with respectives links.
    """
    result = []
    for value in response:
        if "sentinel-2" in value["base_url"]:
            value["bands"] = format_sentinel_band(value)
        else:
            value["bands"] = format_ls_c2_band(value) # ajeitar aqui -> como diferenciar funções para l2 e l1 ?

        result.append(value)

    return result


def format_sentinel_band(value):
    """
    Format base url and generate links to download sentinel bands.

    Parameters
    ----------
        value : dict
            Dictionary with characteristics of a scene (product id, sensing time, etc).

    Returns
    -------
        data : dict
            Dictionary of each bands url.
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


def format_ls_band(value):
    """
    Format base url and generate links to download landsat bands.

    Parameters
    ----------
        value : dict
            Dictionary with characteristics of a scene (product id, sensing time, etc).

    Returns
    -------
        data : dict
            Dictionary of each bands url.
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



 # Product id
    #product = value["product_id"]  

    #x = LC08_L1TP_026027_20200827_20200905_01_T1 | database 
    #y = LC08_L2SP_026027_20200827_20200906_02_T1 | transform processing level: L2SP(Level-2 Science Product), collection number: 02
    #aws s3 ls s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2020/026/027/LC08_L2SP_026027_20200827_20200906_02_T1/LC08_L2SP_026027_20200827_20200906_02_T1_SR_B1.TIF/  --request-payer requester


def format_product(product):
    # Immutable Replacers
    processing_level="L2SP"
    collection = "02"

    # Separate processing date
    identifiers = product.split("_")
    processing_date = identifiers[4]

    #Convert string to datetime object via strptime.
    date_time_obj = datetime.strptime(processing_date, '%Y%m%d')

    # Update processing date by iterarion using timedelta
    newdate = date_time_obj + timedelta(days=1)

    # Converter no formato original para recolocar no product id
    formatted_date = newdate.strftime('%Y%m%d')

    # Replace date in identifiers
    identifiers[4] = formatted_date
    #Replace other identifiers 
    identifiers[1] = processing_level
    identifiers[5] = collection
    print(identifiers)

    newproduct = "_".join(identifiers)

    return newproduct



def format_ls_c2_band(value):
    #Get parameters to build the links
    base_url = LS_L2_URL
    sensor = value["sensor_id"].lower() # replace - por _
    date = parse(str(value["sensing_time"]))
    year = date.year
    product = value["product_id"]
    path = value["wrs_path"]
    row = value["wrs_row"]
    plat = value["spacecraft_id"] #necessario para formatar bandas de acordo com plataforma
    #Format product id
    newproduct = format_product(product)
   
    url_template = "{base_url}/{sensor}/{year}/{path}/{row}/{product}".format(
        base_url=base_url, sensor=sensor, year=year,path=path, row=row, product=newproduct
        )
   
    data = {}
    # Exclude Landsat 1-5
    if plat == LANDSAT_8:
            for band in L8_COG_ITEMS:
                ls_band_template = "{url}/{product_id}_{band}.TIF" # ajeitar aqui

                data[band] = ls_band_template.format(
                    url=url_template, product_id=newproduct, band=band
                )
    elif plat == LANDSAT_7:
            for band in L7_COG_ITEMS:
                ls_band_template = "{url}/{product_id}_{band}.TIF" # ajeitar aqui

                data[band] = ls_band_template.format(
                    url=url_template, product_id=newproduct, band=band
                )

    elif plat == LANDSAT_4 or plat == LANDSAT_5 and sensor == "TM":
            for band in L4_L5_COG_ITEMS:
                ls_band_template = "{url}/{product_id}_{band}.TIF" # ajeitar aqui

                data[band] = ls_band_template.format(
                    url=url_template, product_id=newproduct, band=band
                )
    else: 
        print("There are no images available in collection 2, level 2 for this search.")

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


# references to understanding collections, products types and tiers
# https://www.usgs.gov/core-science-systems/nli/landsat/landsat-collection-1?qt-science_support_page_related_con=1#qt-science_support_page_related_con
# https://www.usgs.gov/core-science-systems/nli/landsat/landsat-collection-2?qt-science_support_page_related_con=1#qt-science_support_page_related_con
# https://www.usgs.gov/media/images/landsat-collection-2-generation-timeline

#NOTE: Landsat Collection 1 based forward processing will remain in effect through December 31, 2021, concurrent with Landsat Collection 2 based forward processing. 
# Starting January 1, 2022, all new Landsat acquisitions will be processed into the Collection 2 inventory structure only. 

#Global Level-2 Science and Atmospheric Auxiliary Products 
# New for Collection 2 is the processing and distribution of Level-2 surface reflectance and surface temperature science products for Landsat 4-5 TM, Landsat 7 ETM+ and Landsat 8 OLI/TIRS. 
# Level-2 products are generated from Collection 2 Level-1 inputs that meet the <76 degrees Solar Zenith Angle constraint and include the required auxiliary data inputs to generate a scientifically viable product.

# Timeline of processing
# Os produtos de Refletância de Superfície e Temperatura de Superfície de Nível 2 estão normalmente disponíveis dentro de 24 horas após uma cena ter sido processada na Camada 1 ou Camada 2: 
# The products of Surface reflectance or Surface Temperature in level 2 are available within 24h after a secne been processed in TIer 1 or Tier 2.

#aws s3 ls s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2020/026/027/LC08_L2SP_026027_20200827_20200906_02_T1/LC08_L2SP_026027_20200827_20200906_02_T1_SR_B1.TIF/  --request-payer requester
