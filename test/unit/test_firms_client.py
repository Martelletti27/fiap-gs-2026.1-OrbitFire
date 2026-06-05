"""Testes do cliente HTTP FIRMS (S1.E1)."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.config import DEFAULT_BBOX
from src.infrastructure.firms.client import FirmsAreaClient

SAMPLE_RESPONSE = "latitude,longitude,acq_date,acq_time\n-16.0,-47.0,2026-06-01,1200\n"


def test_fetch_area_csv_builds_url_and_returns_text() -> None:
    """Cliente deve montar URL area/csv e retornar corpo."""
    client = FirmsAreaClient("chave-teste", max_retries=1)
    mock_response = MagicMock()
    mock_response.text = SAMPLE_RESPONSE
    mock_response.raise_for_status = MagicMock()

    with patch("src.infrastructure.firms.client.requests.get", return_value=mock_response) as get:
        text = client.fetch_area_csv("VIIRS_SNPP_NRT", DEFAULT_BBOX, 3)

    assert text == SAMPLE_RESPONSE
    called_url = get.call_args[0][0]
    assert "/chave-teste/VIIRS_SNPP_NRT/" in called_url
    assert DEFAULT_BBOX.as_firms_area() in called_url
    assert called_url.endswith("/3")


def test_fetch_area_csv_clamps_day_range() -> None:
    """DAY_RANGE deve ficar entre 1 e 5."""
    client = FirmsAreaClient("chave", max_retries=1)
    mock_response = MagicMock()
    mock_response.text = ""
    mock_response.raise_for_status = MagicMock()

    with patch("src.infrastructure.firms.client.requests.get", return_value=mock_response) as get:
        client.fetch_area_csv("MODIS_NRT", DEFAULT_BBOX, 99)

    assert get.call_args[0][0].endswith("/5")


def test_fetch_area_csv_requires_map_key() -> None:
    """MAP_KEY vazia deve falhar antes do HTTP."""
    client = FirmsAreaClient("  ")
    with pytest.raises(ValueError, match="FIRMS_MAP_KEY"):
        client.fetch_area_csv("MODIS_NRT", DEFAULT_BBOX, 1)


def test_fetch_area_csv_retries_on_failure() -> None:
    """Falhas de rede disparam retry configurado."""
    client = FirmsAreaClient("chave", max_retries=2, retry_delay=0)
    ok_response = MagicMock()
    ok_response.text = SAMPLE_RESPONSE
    ok_response.raise_for_status = MagicMock()

    with patch(
        "src.infrastructure.firms.client.requests.get",
        side_effect=[requests.ConnectionError("offline"), ok_response],
    ) as get:
        text = client.fetch_area_csv("MODIS_NRT", DEFAULT_BBOX, 1)

    assert text == SAMPLE_RESPONSE
    assert get.call_count == 2
