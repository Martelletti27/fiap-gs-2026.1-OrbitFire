"""Testes da logica de peso do mapa de calor."""

from src.dashboard.map_view import _build_heat_data, _shadow_rgba


def test_build_heat_data_attenuates_baixo() -> None:
    """Celulas baixo devem ter peso bem menor que alto/critico."""
    cells = [
        {"lat": -10.0, "lon": -48.0, "score": 15.0, "band": "baixo"},
        {"lat": -10.1, "lon": -48.1, "score": 85.0, "band": "critico"},
    ]
    weights = [row[2] for row in _build_heat_data(cells)]
    assert weights[0] < 0.1
    assert weights[1] > 0.5


def test_shadow_rgba_from_hex() -> None:
    """Sombra do marcador usa a mesma cor do preenchimento."""
    assert _shadow_rgba("#c0392b") == "rgba(192,57,43,0.55)"
