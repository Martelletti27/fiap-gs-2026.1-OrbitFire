"""Testes do cliente HTTP do dashboard."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.dashboard.api_client import ApiClientError, OrbitFireApiClient


def test_health_returns_payload() -> None:
    """Cliente deve parsear JSON de /health."""
    client = OrbitFireApiClient("http://test")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok", "region": "Tocantins"}

    with patch(
        "src.dashboard.api_client.requests.get",
        return_value=mock_response,
    ) as get:
        payload = client.health()

    assert payload["status"] == "ok"
    assert get.call_args.args[0] == "http://test/health"


def test_get_raises_on_connection_error() -> None:
    """Falha de rede vira ApiClientError com mensagem acionavel."""
    client = OrbitFireApiClient("http://test")
    with patch(
        "src.dashboard.api_client.requests.get",
        side_effect=requests.exceptions.ConnectionError("offline"),
    ):
        with pytest.raises(ApiClientError, match="API indisponivel"):
            client.health()


def test_fires_summary_calls_endpoint() -> None:
    """Cliente deve chamar /fires/summary com dias."""
    client = OrbitFireApiClient("http://test")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "days": 30,
        "total_in_region": 10,
        "daily_counts": [],
        "by_source": {"VIIRS": 6},
        "monthly_counts": [],
        "cell_ranking": [],
    }

    with patch(
        "src.dashboard.api_client.requests.get",
        return_value=mock_response,
    ) as get:
        payload = client.fires_summary(days=30, top_cells=15)

    assert payload["total_in_region"] == 10
    assert get.call_args.kwargs["params"] == {"days": 30, "top_cells": 15}


def test_get_raises_on_http_error() -> None:
    """Status 404 deve expor detail da API."""
    client = OrbitFireApiClient("http://test")
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.json.return_value = {"detail": "Sem dados"}
    mock_response.text = "Sem dados"

    with patch(
        "src.dashboard.api_client.requests.get",
        return_value=mock_response,
    ):
        with pytest.raises(ApiClientError, match="404"):
            client.risk_map()
