"""Cliente HTTP do Open-Meteo (forecast com past_days)."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from src.config import OPEN_METEO_FORECAST_URL, OPEN_METEO_TIMEZONE

logger = logging.getLogger(__name__)

DAILY_VARIABLES = (
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "wind_speed_10m_max",
)


class OpenMeteoClient:
    """Busca serie diaria de clima para um ponto lat/lon."""

    def __init__(
        self,
        *,
        base_url: str = OPEN_METEO_FORECAST_URL,
        timezone: str = OPEN_METEO_TIMEZONE,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        self._base_url = base_url
        self._timezone = timezone
        self._timeout = timeout
        self._max_retries = max_retries
        self._retry_delay = retry_delay

    def fetch_daily(
        self,
        lat: float,
        lon: float,
        *,
        past_days: int,
        forecast_days: int = 1,
    ) -> dict[str, Any]:
        """Retorna JSON com variaveis diarias para o ponto informado."""
        days = max(1, min(past_days, 92))
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": ",".join(DAILY_VARIABLES),
            "timezone": self._timezone,
            "past_days": days,
            "forecast_days": max(0, forecast_days),
        }
        return self._get_with_retry(params)

    def _get_with_retry(self, params: dict[str, Any]) -> dict[str, Any]:
        """GET com retry simples em falhas de rede ou HTTP 5xx."""
        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                response = requests.get(
                    self._base_url,
                    params=params,
                    timeout=self._timeout,
                )
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                logger.warning(
                    "Open-Meteo fetch falhou (tentativa %s/%s): %s",
                    attempt,
                    self._max_retries,
                    exc,
                )
                if attempt < self._max_retries:
                    time.sleep(self._retry_delay * attempt)

        if last_error is not None:
            raise last_error
        raise RuntimeError("Open-Meteo fetch falhou sem detalhe de erro")
