"""Cliente HTTP da API area/csv da NASA FIRMS."""

from __future__ import annotations

import logging
import time

import requests

from src.config import BBox, FIRMS_BASE_URL

logger = logging.getLogger(__name__)


class FirmsAreaClient:
    """Busca CSV de focos por bbox e produto NASA."""

    def __init__(
        self,
        map_key: str,
        *,
        base_url: str = FIRMS_BASE_URL,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        self._map_key = map_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._retry_delay = retry_delay

    def fetch_area_csv(
        self,
        nasa_source: str,
        bbox: BBox,
        day_range: int,
    ) -> str:
        """Baixa CSV de deteccoes para fonte NASA e janela de dias (1-5)."""
        if not self._map_key.strip():
            raise ValueError("FIRMS_MAP_KEY obrigatoria para ingestao online")

        days = max(1, min(day_range, 5))
        area = bbox.as_firms_area()
        url = f"{self._base_url}/{self._map_key}/{nasa_source}/{area}/{days}"
        return self._get_with_retry(url)

    def _get_with_retry(self, url: str) -> str:
        """GET com retry simples em falhas de rede ou HTTP 5xx."""
        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                response = requests.get(url, timeout=self._timeout)
                response.raise_for_status()
                return response.text
            except requests.RequestException as exc:
                last_error = exc
                logger.warning(
                    "FIRMS fetch falhou (tentativa %s/%s): %s",
                    attempt,
                    self._max_retries,
                    exc,
                )
                if attempt < self._max_retries:
                    time.sleep(self._retry_delay * attempt)

        if last_error is not None:
            raise last_error
        raise RuntimeError("FIRMS fetch falhou sem detalhe de erro")
