"""Cliente HTTP da API OrbitFire para o dashboard."""

from __future__ import annotations

from datetime import date
from typing import Any

import requests

from src.config import Settings, load_settings


class ApiClientError(Exception):
    """Falha ao consultar a API REST."""


class OrbitFireApiClient:
    """Encapsula chamadas GET usadas pelo painel."""

    def __init__(self, base_url: str, *, timeout: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> OrbitFireApiClient:
        """Instancia cliente a partir de Settings."""
        cfg = settings or load_settings()
        return cls(cfg.api_base_url)

    def health(self) -> dict[str, Any]:
        """GET /health."""
        return self._get("/health")

    def risk_map(
        self,
        *,
        reference_date: date | None = None,
        band: str | None = None,
        uf: str | None = None,
    ) -> dict[str, Any]:
        """GET /risk/map com filtros opcionais."""
        params = _date_param(reference_date)
        if band:
            params["band"] = band
        if uf:
            params["uf"] = uf
        return self._get("/risk/map", params)

    def risk_ranking(
        self,
        *,
        reference_date: date | None = None,
        top_n: int = 10,
    ) -> dict[str, Any]:
        """GET /risk/ranking."""
        params: dict[str, Any] = {"top_n": top_n}
        params.update(_date_param(reference_date))
        return self._get("/risk/ranking", params)

    def fires_active(self, *, hours: int = 24) -> dict[str, Any]:
        """GET /fires/active."""
        return self._get("/fires/active", {"hours": hours})

    def fires_summary(
        self,
        *,
        days: int = 30,
        top_cells: int = 15,
    ) -> dict[str, Any]:
        """GET /fires/summary para graficos de comportamento regional."""
        return self._get(
            "/fires/summary",
            {"days": days, "top_cells": top_cells},
        )

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Executa GET JSON com tratamento de erro amigavel."""
        url = f"{self._base_url}{path}"
        try:
            response = requests.get(url, params=params, timeout=self._timeout)
        except requests.RequestException as exc:
            raise ApiClientError(
                "API indisponivel. Execute: uvicorn src.api.main:app --port 8000"
            ) from exc
        if response.status_code >= 400:
            detail = response.json().get("detail", response.text)
            raise ApiClientError(f"Erro {response.status_code}: {detail}")
        return response.json()


def _date_param(reference_date: date | None) -> dict[str, str]:
    """Monta parametro de data ISO quando informado."""
    if reference_date is None:
        return {}
    return {"reference_date": reference_date.isoformat()}
