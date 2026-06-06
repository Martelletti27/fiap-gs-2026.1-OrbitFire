"""Contorno simplificado do Tocantins para filtro geografico no mapa."""

from __future__ import annotations

# Poligono IBGE simplificado (74 vertices, WGS84 lat/lon).
TO_BOUNDARY: tuple[tuple[float, float], ...] = (
    (-5.1719, -48.3562),
    (-5.5956, -47.4844),
    (-6.4016, -47.4199),
    (-7.0504, -47.5748),
    (-7.3787, -47.4982),
    (-7.6213, -47.3721),
    (-7.7412, -47.2612),
    (-7.855, -47.1792),
    (-8.0109, -47.0606),
    (-7.9869, -46.9052),
    (-7.9385, -46.7632),
    (-7.9591, -46.5187),
    (-8.3215, -46.6413),
    (-8.4466, -46.7965),
    (-8.5454, -46.8601),
    (-8.5919, -46.9127),
    (-8.6865, -46.8869),
    (-8.8595, -46.9415),
    (-8.9758, -47.0152),
    (-9.0761, -47.0235),
    (-9.1464, -46.8611),
    (-9.412, -46.741),
    (-9.6658, -46.613),
    (-9.9883, -46.4776),
    (-10.1851, -45.7342),
    (-10.5355, -46.014),
    (-10.8321, -46.2839),
    (-11.4328, -46.5252),
    (-11.6361, -46.0832),
    (-11.803, -46.3316),
    (-12.053, -46.3818),
    (-12.2974, -46.3504),
    (-12.439, -46.2478),
    (-12.6928, -46.2932),
    (-12.9253, -46.1981),
    (-12.9089, -46.3607),
    (-13.014, -46.8189),
    (-13.1214, -47.0011),
    (-13.1785, -47.1326),
    (-13.2497, -47.3089),
    (-13.1899, -47.5098),
    (-13.2141, -47.665),
    (-13.3119, -47.824),
    (-13.2798, -48.0225),
    (-13.307, -48.1508),
    (-13.1686, -48.2169),
    (-13.2284, -48.3421),
    (-13.2496, -48.4607),
    (-13.302, -48.5536),
    (-13.0887, -48.5962),
    (-12.9898, -48.7307),
    (-12.8098, -48.8467),
    (-12.8455, -49.083),
    (-13.0663, -49.3374),
    (-12.9059, -50.0789),
    (-12.8441, -50.2759),
    (-12.6821, -50.286),
    (-12.5436, -50.2229),
    (-12.4782, -50.2632),
    (-12.6425, -50.4273),
    (-12.8436, -50.5319),
    (-12.6135, -50.7061),
    (-12.1239, -50.676),
    (-11.4714, -50.7391),
    (-10.8, -50.5916),
    (-10.1709, -50.3969),
    (-9.4754, -50.1053),
    (-8.6394, -49.4638),
    (-7.7938, -49.1579),
    (-6.8889, -49.1504),
    (-6.3756, -48.3813),
    (-5.71, -48.1736),
    (-5.3737, -48.7203),
    (-5.1719, -48.3562),
)


def is_in_tocantins(lat: float, lon: float) -> bool:
    """Indica se o ponto esta dentro do poligono simplificado do TO."""
    return _point_in_polygon(lat, lon, TO_BOUNDARY)


def boundary_bounds() -> tuple[float, float, float, float]:
    """Retorna lat_min, lat_max, lon_min, lon_max do contorno."""
    lats = [point[0] for point in TO_BOUNDARY]
    lons = [point[1] for point in TO_BOUNDARY]
    return min(lats), max(lats), min(lons), max(lons)


def _point_in_polygon(
    lat: float,
    lon: float,
    polygon: tuple[tuple[float, float], ...],
) -> bool:
    """Ray casting em poligono fechado (lat, lon)."""
    inside = False
    total = len(polygon)
    j = total - 1
    for i in range(total):
        lat_i, lon_i = polygon[i]
        lat_j, lon_j = polygon[j]
        intersects = (lat_i > lat) != (lat_j > lat) and lon < (
            (lon_j - lon_i) * (lat - lat_i) / (lat_j - lat_i + 1e-15) + lon_i
        )
        if intersects:
            inside = not inside
        j = i
    return inside
