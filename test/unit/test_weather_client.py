"""Testes do cliente Open-Meteo (S1.E2)."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.infrastructure.weather.client import OpenMeteoClient

SAMPLE_JSON = {
    "daily": {
        "time": ["2026-06-01"],
        "temperature_2m_max": [30.0],
        "temperature_2m_min": [18.0],
        "precipitation_sum": [0.5],
        "wind_speed_10m_max": [3.0],
    }
}


def test_fetch_daily_returns_json() -> None:
    """Cliente deve chamar forecast API e retornar JSON."""
    client = OpenMeteoClient(max_retries=1)
    mock_response = MagicMock()
    mock_response.json.return_value = SAMPLE_JSON
    mock_response.raise_for_status = MagicMock()

    with patch(
        "src.infrastructure.weather.client.requests.get",
        return_value=mock_response,
    ) as get:
        payload = client.fetch_daily(-15.8, -47.9, past_days=7)

    assert payload == SAMPLE_JSON
    params = get.call_args.kwargs["params"]
    assert params["latitude"] == -15.8
    assert params["longitude"] == -47.9
    assert params["past_days"] == 7
    assert "temperature_2m_max" in params["daily"]


def test_fetch_daily_retries_on_failure() -> None:
    """Falhas de rede disparam retry configurado."""
    client = OpenMeteoClient(max_retries=2, retry_delay=0)
    ok_response = MagicMock()
    ok_response.json.return_value = SAMPLE_JSON
    ok_response.raise_for_status = MagicMock()

    with patch(
        "src.infrastructure.weather.client.requests.get",
        side_effect=[requests.ConnectionError("offline"), ok_response],
    ) as get:
        payload = client.fetch_daily(-16.0, -49.1, past_days=3)

    assert payload == SAMPLE_JSON
    assert get.call_count == 2
