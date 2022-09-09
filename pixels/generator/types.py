from collections import namedtuple
from typing import TypeVar

XShape3D = namedtuple("XShape3D", ["batch", "timesteps", "height", "width", "bands"])
# batch = batch * timesteps
XShape2D = namedtuple("XShape2D", ["batch", "height", "width", "bands"])
XShape1D = namedtuple("XShape1D", ["batch", "timesteps", "bands"])

YShapeND = namedtuple("YShapeND", ["batch", "height", "width", "classes"])
YShape1D = namedtuple("YShape1D", ["batch", "classes"])

XShape = TypeVar("XShape", XShape1D, XShape2D, XShape3D)
YShape = TypeVar("YShape", YShape1D, YShapeND)

# RESNET -> Batch, batch * (number of moving windoe on each batch)
