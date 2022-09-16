from typing import Optional, Union

from pydantic import BaseModel, Extra, root_validator

from pixels.generator.generator import (
    GENERATOR_3D_MODEL,
    GENERATOR_MODE_TRAINING,
    GENERATOR_PIXEL_MODEL,
)


class GeneratorArgumentsValidator(BaseModel, extra=Extra.forbid):
    path_collection_catalog: Optional[str] = ""
    split: Optional[float] = 1
    random_seed: Optional[float] = None
    timesteps: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    y_width: Optional[int] = None
    y_height: Optional[int] = None
    num_bands: Optional[int] = None
    num_classes: Optional[int] = 1
    upsampling: Optional[int] = 1
    mode: Optional[str] = (GENERATOR_3D_MODEL,)
    batch_number: Optional[int] = 1
    padding: Optional[int] = 0
    y_padding: Optional[int] = 0
    x_nan_value: Optional[Union[int, float]] = 0
    y_nan_value: Optional[Union[int, float]] = None
    nan_value: Optional[Union[int, float]] = None
    padding_mode: Optional[str] = "edge"
    dtype: Optional[str] = None
    augmentation: Optional[int] = 0
    training_percentage: Optional[float] = 1
    usage_type: Optional[str] = GENERATOR_MODE_TRAINING
    class_definitions: Optional[Union[int, list]] = None
    y_max_value: Optional[Union[int, float]] = None
    class_weights: Optional[dict] = None
    download_data: Optional[bool] = False
    download_dir: Optional[str] = None
    normalization: Optional[Union[int, float]] = None
    shuffle: Optional[bool] = True
    one_hot: Optional[bool] = True
    cloud_sort: Optional[bool] = False
    framed_window: Optional[int] = 3
    train_with_array: Optional[bool] = False
    eval_split: Optional[float] = 1

    @root_validator(pre=True)
    def validate_train_with_array_for_1d(cls, values):
        if values.get("mode", None) == GENERATOR_PIXEL_MODEL and not (
            values.get("train_with_array", None)
        ):
            raise ValueError("Use train_with_array for 1D models")
        return values

    @root_validator(pre=True)
    def validate_y_max_with_class_definitions(cls, values):
        if (
            isinstance(values.get("class_definitions"), int)
            and values.get("y_max_value") is None
        ):
            raise ValueError(
                "For multiclass builder with number of classes, "
                "a y_max_value must be provided."
            )
        return values
