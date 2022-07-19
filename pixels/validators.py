from datetime import date
from enum import Enum
from typing import List, Optional, Union

from geojson_pydantic.features import FeatureCollection
from pydantic import BaseModel, Extra, root_validator, validator
from rasterio.crs import CRS
from rasterio.errors import CRSError


class LandsatPlatform(str, Enum):
    landsat_1 = "LANDSAT_1"
    landsat_2 = "LANDSAT_2"
    landsat_3 = "LANDSAT_3"
    landsat_4 = "LANDSAT_4"
    landsat_5 = "LANDSAT_5"
    landsat_6 = "LANDSAT_6"
    landsat_7 = "LANDSAT_7"
    landsat_8 = "LANDSAT_8"


class SentinelPlatform(str, Enum):
    sentinel_2 = "SENTINEL_2"


class PlatformOption(str, Enum):
    landsat_1 = "LANDSAT_1"
    landsat_2 = "LANDSAT_2"
    landsat_3 = "LANDSAT_3"
    landsat_4 = "LANDSAT_4"
    landsat_5 = "LANDSAT_5"
    landsat_6 = "LANDSAT_6"
    landsat_7 = "LANDSAT_7"
    landsat_8 = "LANDSAT_8"
    sentinel_2 = "SENTINEL_2"


class TimeStepOption(str, Enum):
    all = "all"
    weeks = "weeks"
    months = "months"


class ModeOption(str, Enum):
    latest_pixel = "latest_pixel"
    cloud_sorted_pixel = "cloud_sorted_pixel"
    composite = "composite"
    all = "all"


class CompositeMethodOption(str, Enum):
    index = "INDEX"
    scl = "SCL"
    full = "FULL"


class LandsatLevelOption(str, Enum):
    l1 = "L1"
    l2 = "L2"


class SentinelLevelOption(str, Enum):
    l2a = "L2A"
    l1c = "L1C"


class FeatureCollectionCRS(FeatureCollection):
    crs: Optional[dict] = {"init": "EPSG:4326"}

    @validator("crs")
    def validate_crs(cls, v):
        try:
            CRS.from_dict(v)
        except CRSError:
            raise ValueError("crs dictionary is not valid")
        return v

    @property
    def rasterio_crs(self):
        return CRS(self.crs)


class SearchOrderOption(str, Enum):
    cloud_cover = "cloud_cover"
    sensing_time = "sensing_time"


class Sentinel2PlatformOption(str, Enum):
    sentinel_2a = "sentinel-2a"
    sentinel_2b = "sentinel-2b"
    sentinel_2c = "sentinel-2c"
    sentinel_2d = "sentinel-2d"


class SearchStacCollectionOption(str, Enum):
    landsat_8_l1_c1 = "landsat-8-l1-c1"
    landsat_c1l1_ = "landsat-c1l1"
    landsat_c1l2alb_bt = "landsat-c1l2alb-bt"
    landsat_c1l2alb_sr = "landsat-c1l2alb-sr"
    landsat_c1l2alb_st = "landsat-c1l2alb-st"
    landsat_c1l2alb_ta = "landsat-c1l2alb-ta"
    landsat_c2ard_bt = "landsat-c2ard-bt"
    landsat_c2ard_sr = "landsat-c2ard-sr"
    landsat_c2ard_st = "landsat-c2ard-st"
    landsat_c2ard_ta = "landsat-c2ard-ta"
    landsat_c2l1 = "landsat-c2l1"
    landsat_c2l2alb_bt = "landsat-c2l2alb-bt"
    landsat_c2l2alb_sr = "landsat-c2l2alb-sr"
    landsat_c2l2alb_st = "landsat-c2l2alb-st"
    landsat_c2l2alb_ta = "landsat-c2l2alb-ta"
    landsat_c2l2_sr = "landsat-c2l2-sr"
    landsat_c2l2_st = "landsat-c2l2-st"
    landsat_c2l3_ba = "landsat-c2l3-ba"
    landsat_c2l3_dswe = "landsat-c2l3-dswe"
    landsat_c2l3_fsca = "landsat-c2l3-fsca"
    sentinel_s2_l1c = "sentinel-s2-l1c"
    sentinel_s2_l2a = "sentinel-s2-l2a"
    sentinel_s2_l2a_cogs = "sentinel-s2-l2a-cogs"


class PixelsBaseValidator(BaseModel, extra=Extra.forbid):
    geojson: FeatureCollectionCRS
    start: Optional[str]
    end: Optional[str]
    platforms: Union[
        LandsatPlatform, SentinelPlatform, List[LandsatPlatform], List[SentinelPlatform]
    ]
    maxcloud: int = 20
    level: Optional[Union[SentinelLevelOption, LandsatLevelOption]]
    limit: Optional[int]
    bands: Union[list, tuple]

    @validator("start", "end")
    def is_date(cls, v):
        date.fromisoformat(v)
        return v

    @validator("platforms")
    def validate_platform_list(cls, v):
        if isinstance(v, str):
            v = [v]
        elif len(v) != 1:
            raise ValueError("Exactly one platform can be requested")
        PlatformOption(v[0])
        return v

    @validator("level")
    def check_level(cls, v, values):
        platforms = values.get("platforms", [])
        if v == LandsatLevelOption.l2:
            [LandsatPlatform(platform) for platform in platforms]
        elif (
            v in list(SentinelLevelOption)
            and SentinelPlatform.sentinel_2 not in platforms
        ):
            raise ValueError(f"Level {v} is only for Sentinel-2")
        return v

    @root_validator(pre=True)
    def check_scl_level(cls, values):
        if (
            "SCL" in values.get("bands", [])
            and values.get("level") != SentinelLevelOption.l2a
        ):
            raise ValueError("SCL can only be requested for level L2A")
        return values


class PixelsConfigValidator(PixelsBaseValidator, extra=Extra.forbid):
    dynamic_dates_step: int = 1
    interval: TimeStepOption = TimeStepOption.all
    interval_step: int = 1
    scale: float = 10
    clip: bool = True
    pool_size: int = 0
    pool_bands: bool = False
    mode: ModeOption = ModeOption.latest_pixel
    dynamic_dates_interval: Optional[TimeStepOption]
    composite_method: Optional[CompositeMethodOption] = CompositeMethodOption.scl

    @validator("interval_step", "scale", "maxcloud", "limit", "dynamic_dates_step")
    def is_positive(cls, v, field):
        if v <= 0:
            raise ValueError(f"{field} needs to be a positive number")
        return v

    @root_validator(pre=True)
    def non_dynamic_start(cls, values):
        if not values.get("start") and not values.get("dynamic_dates_interval"):
            raise ValueError("Start date is required for non dynamic dates")
        return values

    @validator("composite_method")
    def check_composite_method(cls, v, values):
        if v and not values.get("mode") == ModeOption.composite:
            raise ValueError("Composite method is only used in composite mode.")
        return v

    @validator("pool_bands")
    def check_pool_bands(cls, v, values):
        if v and values.get("pool_size") > 1:
            raise ValueError("Bands pooling can not be combined with dates pooling")


class PixelsSearchValidator(PixelsBaseValidator):
    sort: SearchOrderOption = SearchOrderOption.sensing_time

    @property
    def query_platforms(self):
        result = [
            platform for platform in self.platforms if platform in LandsatPlatform
        ]
        if SentinelPlatform.sentinel_2 in self.platforms:
            result += list(Sentinel2PlatformOption)
        return result

    @property
    def query_collections(self):
        collections = []
        if any([platform in LandsatPlatform for platform in self.platforms]):
            collections.append(SearchStacCollectionOption.landsat_c2l2_sr)

        if any([platform in SentinelPlatform for platform in self.platforms]):
            if self.level == SentinelLevelOption.l2a:
                collections.append(SearchStacCollectionOption.sentinel_s2_l2a)
                collections.append(SearchStacCollectionOption.sentinel_s2_l2a_cogs)
            else:
                collections.append(SearchStacCollectionOption.sentinel_s2_l1c)

        return collections
