"""Testes do contorno simplificado do Tocantins."""

from src.domain.to_boundary import boundary_bounds, is_in_tocantins


def test_palmas_is_inside_tocantins() -> None:
    """Capital do TO deve estar dentro do poligono."""
    assert is_in_tocantins(-10.1840, -48.3336)


def test_belem_is_outside_tocantins() -> None:
    """Belem (PA) fica fora do contorno do TO."""
    assert not is_in_tocantins(-1.4558, -48.4902)


def test_boundary_bounds_cover_state() -> None:
    """Limites do poligono devem abranger o estado."""
    lat_min, lat_max, lon_min, lon_max = boundary_bounds()
    assert lat_min < -13.0
    assert lat_max > -5.5
    assert lon_min < -50.0
    assert lon_max > -46.0
