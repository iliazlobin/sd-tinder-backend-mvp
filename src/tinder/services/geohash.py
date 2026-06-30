"""Geohash service — encode/decode, neighbor prefixes, distance."""

from __future__ import annotations

import pygeohash as pgh  # type: ignore[import-untyped]


def encode(lat: float, lon: float, precision: int = 7) -> str:
    """Encode lat/lon to a geohash string."""
    return pgh.encode(lat, lon, precision)


def decode(geohash: str) -> tuple[float, float]:
    """Decode a geohash string to (lat, lon) center."""
    ll = pgh.decode(geohash)
    return (ll.latitude, ll.longitude)


def prefix(geohash: str, length: int = 5) -> str:
    """Return the geohash prefix for broader neighbor queries."""
    return geohash[:length]


def neighbors(geohash: str) -> list[str]:
    """Return all 9 cells covering this geohash (self + 8 neighbors)."""
    result = [geohash]
    # Cardinal directions
    for direction in ("right", "left", "top", "bottom"):
        try:
            result.append(pgh.get_adjacent(geohash, direction))
        except (ValueError, KeyError):
            pass

    # Diagonal = two cardinal moves
    diagonals = [
        ("top", "right"),
        ("top", "left"),
        ("bottom", "right"),
        ("bottom", "left"),
    ]
    for d1, d2 in diagonals:
        try:
            mid = pgh.get_adjacent(geohash, d1)
            result.append(pgh.get_adjacent(mid, d2))
        except (ValueError, KeyError):
            pass

    return result


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in meters between two lat/lon pairs."""
    gh1 = encode(lat1, lon1, precision=7)
    gh2 = encode(lat2, lon2, precision=7)
    return pgh.geohash_haversine_distance(gh1, gh2)


def meters_to_km(meters: float) -> float:
    """Convert meters to kilometers."""
    return meters / 1000.0
