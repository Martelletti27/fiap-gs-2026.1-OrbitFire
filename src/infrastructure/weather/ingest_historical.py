"""Job de ingestao de clima historico (Open-Meteo archive) para treino."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.config import (
    OPEN_METEO_ARCHIVE_URL,
    TRAIN_PERIOD_END,
    TRAIN_PERIOD_START,
    WEATHER_ARCHIVE_MAX_RETRIES,
    WEATHER_ARCHIVE_RATE_LIMIT_DELAY_SEC,
    WEATHER_REQUEST_DELAY_SEC,
    Settings,
    ensure_data_dirs,
    load_settings,
)
from src.infrastructure.db.repository import OrbitFireRepository, repository_session
from src.infrastructure.weather.client import OpenMeteoClient
from src.infrastructure.weather.ingest import WeatherIngestResult, _persist_records
from src.infrastructure.weather.parser import parse_open_meteo_daily
from src.infrastructure.weather.targets import WeatherTarget, resolve_weather_targets

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WeatherHistoricalSummary:
    """Resumo agregado da ingestao historica de clima."""

    cells: int
    complete: int
    fetched: int
    inserted: int
    skipped: int
    failed: int
    pending: int


def run_weather_historical_ingest(
    settings: Settings | None = None,
) -> list[WeatherIngestResult]:
    """Baixa clima archive jun-set/2024 por celula; resiliente a falhas por celula."""
    cfg = settings or load_settings()
    ensure_data_dirs(cfg)

    if cfg.offline_mode:
        raise ValueError("Ingestao historica de clima requer OFFLINE_MODE=0")

    expected_days = (TRAIN_PERIOD_END - TRAIN_PERIOD_START).days + 1
    client = OpenMeteoClient(
        base_url=OPEN_METEO_ARCHIVE_URL,
        max_retries=WEATHER_ARCHIVE_MAX_RETRIES,
        rate_limit_base_delay=WEATHER_ARCHIVE_RATE_LIMIT_DELAY_SEC,
    )

    with repository_session(cfg.db_path) as repository:
        targets = resolve_weather_targets(cfg, repository)
        if not targets:
            raise ValueError("Nenhum alvo de clima encontrado para ingestao historica")

        total_cells = len(targets)
        complete_count = _count_complete_cells(repository, targets, expected_days)
        results: list[WeatherIngestResult] = []

        for index, target in enumerate(targets):
            if _cell_period_complete(repository, target.cell_id, expected_days):
                results.append(
                    WeatherIngestResult(
                        cell_id=target.cell_id,
                        fetched=0,
                        inserted=0,
                        skipped=expected_days,
                    )
                )
                _print_progress(complete_count, total_cells)
                continue

            if index > 0 and WEATHER_REQUEST_DELAY_SEC > 0:
                time.sleep(WEATHER_REQUEST_DELAY_SEC)

            try:
                result = _ingest_cell_period(
                    cfg,
                    repository,
                    client,
                    target,
                )
                results.append(result)
            except Exception as exc:
                logger.warning(
                    "Clima historico %s: falhou, pulando (%s)",
                    target.cell_id,
                    exc,
                )
                results.append(
                    WeatherIngestResult(
                        cell_id=target.cell_id,
                        fetched=0,
                        inserted=0,
                        skipped=0,
                        failed=True,
                    )
                )

            if _cell_period_complete(repository, target.cell_id, expected_days):
                complete_count += 1

            _print_progress(complete_count, total_cells)

        return results


def summarize_historical(
    results: list[WeatherIngestResult],
    *,
    total_cells: int,
    complete_cells: int,
) -> WeatherHistoricalSummary:
    """Agrega contadores da ingestao historica de clima."""
    failed = sum(1 for item in results if item.failed)
    pending = total_cells - complete_cells
    return WeatherHistoricalSummary(
        cells=len(results),
        complete=complete_cells,
        fetched=sum(item.fetched for item in results),
        inserted=sum(item.inserted for item in results),
        skipped=sum(item.skipped for item in results),
        failed=failed,
        pending=pending,
    )


def _count_complete_cells(
    repository: OrbitFireRepository,
    targets: list[WeatherTarget],
    expected_days: int,
) -> int:
    """Quantas celulas ja tem o periodo historico completo."""
    return sum(
        1
        for target in targets
        if _cell_period_complete(repository, target.cell_id, expected_days)
    )


def _cell_period_complete(
    repository: OrbitFireRepository,
    cell_id: str,
    expected_days: int,
) -> bool:
    """Indica se celula ja tem todos os dias do periodo de treino."""
    existing = repository.count_weather_days_for_cell_in_range(
        cell_id,
        TRAIN_PERIOD_START,
        TRAIN_PERIOD_END,
    )
    return existing >= expected_days


def _ingest_cell_period(
    cfg: Settings,
    repository: OrbitFireRepository,
    client: OpenMeteoClient,
    target: WeatherTarget,
) -> WeatherIngestResult:
    """Busca e persiste clima historico de uma celula."""
    payload = client.fetch_historical_daily(
        target.lat,
        target.lon,
        start_date=TRAIN_PERIOD_START,
        end_date=TRAIN_PERIOD_END,
    )
    raw_path = _save_raw_json(cfg.raw_weather_dir, target.cell_id, payload)
    records = parse_open_meteo_daily(payload)
    inserted, skipped = _persist_records(repository, target.cell_id, records)
    logger.info(
        "Clima historico %s: fetched=%s inserted=%s skipped=%s",
        target.cell_id,
        len(records),
        inserted,
        skipped,
    )
    return WeatherIngestResult(
        cell_id=target.cell_id,
        fetched=len(records),
        inserted=inserted,
        skipped=skipped,
        raw_path=raw_path,
    )


def _print_progress(complete_count: int, total_cells: int) -> None:
    """Exibe percentual de celulas com periodo historico completo."""
    percent = 100.0 * complete_count / total_cells if total_cells else 0.0
    print(
        f"Progresso clima: {complete_count}/{total_cells} ({percent:.1f}%)",
        flush=True,
    )


def _save_raw_json(raw_dir: Path, cell_id: str, payload: dict) -> Path:
    """Grava snapshot bruto do archive em data/raw/weather/."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_id = cell_id.replace("/", "_")
    path = raw_dir / f"hist_{safe_id}_{stamp}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def main() -> None:
    """Entrypoint: python -m src.infrastructure.weather.ingest_historical"""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    cfg = load_settings()
    expected_days = (TRAIN_PERIOD_END - TRAIN_PERIOD_START).days + 1
    with repository_session(cfg.db_path) as repository:
        targets = resolve_weather_targets(cfg, repository)
        total_cells = len(targets)
        complete_before = _count_complete_cells(repository, targets, expected_days)
    print(
        f"Inicio: {complete_before}/{total_cells} "
        f"({100.0 * complete_before / total_cells:.1f}%) celulas completas",
        flush=True,
    )
    results = run_weather_historical_ingest(cfg)
    with repository_session(cfg.db_path) as repository:
        targets = resolve_weather_targets(cfg, repository)
        complete_after = _count_complete_cells(repository, targets, expected_days)
    summary = summarize_historical(
        results,
        total_cells=total_cells,
        complete_cells=complete_after,
    )
    print(
        f"Clima historico {TRAIN_PERIOD_START}..{TRAIN_PERIOD_END}: "
        f"completas={summary.complete}/{total_cells} "
        f"fetched={summary.fetched} inserted={summary.inserted} "
        f"skipped={summary.skipped} falhas={summary.failed} "
        f"pendentes={summary.pending}"
    )


if __name__ == "__main__":
    main()
