"""Geometry helpers: reprojection, inward buffer, area."""

from __future__ import annotations

from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

from .config import ALBERS, INWARD_BUFFER_M, PIXEL_M, WGS84


def reproject(geom: BaseGeometry, src: int, dst: int) -> BaseGeometry:
    t = Transformer.from_crs(src, dst, always_xy=True)
    return transform(t.transform, geom)


def to_albers(geom_wgs84: BaseGeometry) -> BaseGeometry:
    return reproject(geom_wgs84, WGS84, ALBERS)


def to_wgs84(geom_albers: BaseGeometry) -> BaseGeometry:
    return reproject(geom_albers, ALBERS, WGS84)


def interior(geom_wgs84: BaseGeometry, buffer_m: float = INWARD_BUFFER_M) -> BaseGeometry:
    """Field polygon shrunk inward by one pixel, returned in WGS84 (handoff §8.1 step 2)."""
    return to_wgs84(to_albers(geom_wgs84).buffer(-buffer_m))


def area_ha(geom_wgs84: BaseGeometry) -> float:
    return to_albers(geom_wgs84).area / 1e4


def approx_pixels(geom_wgs84: BaseGeometry, pixel_m: float = PIXEL_M) -> int:
    return int(to_albers(geom_wgs84).area // (pixel_m**2))


def as_geojson(geom: BaseGeometry) -> dict:
    return mapping(geom)


def from_geojson(obj: dict) -> BaseGeometry:
    return shape(obj)
