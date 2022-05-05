from datetime import date
from enum import Enum
from typing import Optional, Union

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
    crs: dict

    @validator("crs")
    def validate_crs(cls, v):
        try:
            CRS.from_dict(v)
        except CRSError:
            raise ValueError("crs dictionary is not valid")
        return v


class PixelsConfigValidator(BaseModel, extra=Extra.forbid):
    dynamic_dates_step: int = 1
    start: Optional[str]
    end: Optional[str]
    interval: TimeStepOption = TimeStepOption.all
    interval_step: int = 1
    scale: float = 10
    clip: bool = True
    maxcloud: int = 20
    pool_size: int = 0
    platforms: Union[LandsatPlatform, SentinelPlatform, list, tuple]
    level: Optional[Union[SentinelLevelOption, LandsatLevelOption]]
    bands: Union[list, tuple]
    limit: Optional[int]
    mode: ModeOption = ModeOption.latest_pixel
    dynamic_dates_interval: Optional[TimeStepOption]
    geojson: FeatureCollectionCRS
    composite_method: Optional[CompositeMethodOption] = CompositeMethodOption.scl

    @validator("start", "end")
    def is_date(cls, v):
        date.fromisoformat(v)
        return v

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

    @validator("bands")
    def check_scl_level(cls, v, values):
        if "SCL" in v and values["level"] != "L2A":
            raise ValueError("SCL can only be requested for level L2A")
        return v

    @validator("composite_method")
    def check_composite_method(cls, v, values):
        if v and not values.get("mode") == ModeOption.composite:
            raise ValueError("Composite method is only used in composite mode.")
        return v
