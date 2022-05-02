from datetime import date
from enum import Enum
from typing import Optional, Union

from geojson_pydantic.features import FeatureCollection
from pydantic import BaseModel, root_validator, validator
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
    composite = "composite"


class LandsatLevelOption(str, Enum):
    l1 = "L1"
    l2 = "L2"


class SentinelLevelOption(str, Enum):
    l2a = "L2A"
    l1c = "L1C"


class FeatureCollectionCRS(FeatureCollection):
    crs: dict

    @validator("crs")
    def validate_crs(cls, v):
        try:
            CRS.from_dict(v)
        except CRSError:
            raise ValueError("crs dictionary is not valid")
        return v


class PixelsConfigValidator(BaseModel):
    start: Optional[str]
    end: Optional[str]
    interval: TimeStepOption = TimeStepOption.all
    interval_step: int = 1
    scale: float = 10
    clip: bool = True
    bands: Union[list, tuple]
    maxcloud: int = 20
    pool_size: int = 0
    level: Optional[Union[SentinelLevelOption, LandsatLevelOption]]
    platforms: Union[LandsatPlatform, SentinelPlatform, list, tuple]
    limit: Optional[int]
    mode: ModeOption = ModeOption.latest_pixel
    dynamic_dates_interval: Optional[TimeStepOption]
    dynamic_dates_step: int = 1
    geojson: FeatureCollectionCRS

    @validator("start", "end")
    def is_date(cls, v):
        date.fromisoformat(v)
        return v

    @validator("start")
    def non_dynamic_start(cls, v, values):
        if not v and not values.get("dynamic_dates_interval"):
            raise ValueError("Start date is required for non dynamic dates")
        return v

    @validator("interval_step", "scale", "maxcloud", "limit", "dynamic_dates_step")
    def is_positive(cls, v, field):
        if v <= 0:
            raise ValueError(f"{field} needs to be a positive number")
        return v

    @validator("platforms")
    def validate_platform_list(cls, v):
        if isinstance(v, str):
            v = [v]
        elif len(v) != 1:
            raise ValueError("Exactly one platform can be requested")
        PlatformOption(v[0])
        return v

    @root_validator()
    def check_scl_level(cls, values):
        if "SCL" in values["bands"] and values["level"] != "L2A":
            raise ValueError("SCL can only be requested for level L2A")
        return values

    @validator("level")
    def check_level(cls, v, values):
        if v == LandsatLevelOption.l2:
            [LandsatPlatform(platform) for platform in values["platforms"]]
        elif (
            v in list(SentinelLevelOption)
            and SentinelPlatform.sentinel_2 not in values["platforms"]
        ):
            raise ValueError(f"Level {v} is only for Sentinel-2")
        return v
