from pixels.config.db_config import create_db_engine_pxsearch
from pixels.log import logger
from pixels.utils import compute_wgs83_bbox
from pixels.validators import PixelsSearchValidator, SearchOrderOption

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


def build_query(data: PixelsSearchValidator):
    xmin, ymin, xmax, ymax = compute_wgs83_bbox(data.geojson, return_bbox=True)

    query = f"""
    SELECT id, collection_id, datetime, properties, assets FROM data.items
    WHERE ST_Intersects(ST_MakeEnvelope({xmin}, {ymin},{xmax},{ymax},4326), geometry)
    AND (properties ->> 'platform') IN ({prep_in_array_query(data.query_platforms)})
    """

    if data.query_collections:
        query += (
            f" AND collection_id IN ({prep_in_array_query(data.query_collections)})"
        )

    if data.start is not None:
        query += f" AND datetime >= timestamp '{data.start}' "
    if data.end is not None:
        query += f" AND datetime <= timestamp '{data.end}' "
    if data.maxcloud is not None:
        query += f" AND (properties -> 'eo:cloud_cover')::float < {data.maxcloud}"
    if data.sort == SearchOrderOption.cloud_cover:
        query += " ORDER BY properties -> 'eo:cloud_cover' ASC"
    elif data.sort:
        query += " ORDER BY datetime DESC"
    if data.limit is not None:
        query += " LIMIT {}".format(data.limit)

    return query


def search_data(data: PixelsSearchValidator):

    query = build_query(data)
    query_results = execute_query(query)

    result = []
    for item in query_results:
        item_bands_hrefs = {}
        for asset_key, asset in item["assets"].items():
            band_name = determine_band_name(asset_key, asset, data.bands)
            if not band_name:
                continue

            if "alternate" in asset:
                item_bands_hrefs[band_name] = asset["alternate"]["s3"]["href"]
            else:
                item_bands_hrefs[band_name] = asset["href"]

        missing_bands = set(data.bands) - set(item_bands_hrefs.keys())
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
