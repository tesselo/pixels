from pixels.config.db_config import create_db_engine_pxsearch
from pixels.log import logger
from pixels.utils import compute_wgs83_bbox

engine = create_db_engine_pxsearch()


def prep_in_array_query(data):
    return ",".join("'" + dat + "'" for dat in data)


def execute_query(query):
    connection = engine.connect(close_with_result=True)
    db_result = connection.execute(query)
    return [dict(row) for row in db_result]


def match_eo_bands_extension_names(asset, bands):
    return len(asset.get("eo:bands", [])) == 1 and asset["eo:bands"][0]["name"] in bands


def determine_band_name(asset_key, asset, bands):
    if asset_key in bands:
        return asset_key
    if match_eo_bands_extension_names(asset, bands):
        return asset["eo:bands"][0]["name"]
    return None


def search_data(
    geojson,
    start=None,
    end=None,
    platforms=None,
    maxcloud=None,
    level=None,
    limit=10,
    sort="sensing_time",
    bands=None,
):

    xmin, ymin, xmax, ymax = compute_wgs83_bbox(geojson, return_bbox=True)

    query = f"""
    SELECT id, collection_id, datetime, properties, assets FROM data.items
    WHERE ST_Intersects(ST_MakeEnvelope({xmin}, {ymin},{xmax},{ymax},4326), geometry)
    """

    collections = []
    if any(["LANDSAT" in platform for platform in platforms]):
        collections.append("landsat-c2l2-sr")
    if any(["SENTINEL_2" == platform for platform in platforms]):
        if level == "L2A":
            collections.append("sentinel-s2-l2a-cogs")
        else:
            collections.append("sentinel-s2-l1c")
    if collections:
        query += f" AND collection_id IN ({prep_in_array_query(collections)})"

    if start is not None:
        query += f" AND datetime >= timestamp '{start}' "
    if end is not None:
        query += f" AND datetime <= timestamp '{end}' "
    if maxcloud is not None:
        query += f" AND (properties -> 'eo:cloud_cover')::float < {maxcloud}"
    if sort == "cloud_cover":
        query += " ORDER BY properties -> 'eo:cloud_cover' ASC"
    elif sort:
        query += " ORDER BY datetime DESC"
    if limit is not None:
        query += " LIMIT {}".format(limit)

    query_results = execute_query(query)

    result = []
    for item in query_results:
        # Skip unwanted landsat platforms.
        platform = item["properties"].get("platform")
        if "sentinel" not in platform and platform not in platforms:
            continue

        item_bands_hrefs = {}
        for asset_key, asset in item["assets"].items():
            band_name = determine_band_name(asset_key, asset, bands)
            if not band_name:
                continue

            if "alternate" in asset:
                item_bands_hrefs[band_name] = asset["alternate"]["s3"]["href"]
            else:
                item_bands_hrefs[band_name] = asset["href"]

        missing_bands = set(bands) - set(item_bands_hrefs.keys())
        if missing_bands:
            logger.warning(f"Bands {missing_bands} not found in item {item['id']}")

        result.append(
            {
                "id": item["id"],
                "sensing_time": item["datetime"],
                "bands": item_bands_hrefs,
                "cloud_cover": item["properties"].get("eo:cloud_cover", None),
            }
        )

    return result
