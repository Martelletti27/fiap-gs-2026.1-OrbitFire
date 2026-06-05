"""Job de ingestao de clima: Open-Meteo ou seed offline."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.config import WEATHER_DAY_RANGE, Settings, ensure_data_dirs, load_settings
from src.infrastructure.db.repository import OrbitFireRepository, open_repository, tally_insert
from src.infrastructure.seed.loader import load_weather_seed_if_offline
from src.infrastructure.weather.client import OpenMeteoClient
from src.infrastructure.weather.parser import ParsedWeatherDaily, parse_open_meteo_daily
from src.infrastructure.weather.targets import WeatherTarget, resolve_weather_targets

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WeatherIngestResult:
    """Resumo da ingestao de clima por alvo ou modo offline."""

    cell_id: str
    fetched: int
    inserted: int
    skipped: int
    raw_path: Path | None = None


def run_weather_ingest(settings: Settings | None = None) -> list[WeatherIngestResult]:
    """Executa ingestao de clima conforme OFFLINE_MODE e persiste em weather_daily."""
    cfg = settings or load_settings()
    ensure_data_dirs(cfg)

    if cfg.offline_mode:
        return _ingest_offline(cfg)

    client = OpenMeteoClient()
    repository, session, engine = open_repository(cfg.db_path)
    try:
        targets = resolve_weather_targets(cfg, repository)
        if not targets:
            raise ValueError("Nenhum alvo de clima encontrado para ingestao")

        results: list[WeatherIngestResult] = []
        for target in targets:
            payload = client.fetch_daily(
                target.lat,
                target.lon,
                past_days=WEATHER_DAY_RANGE,
            )
            raw_path = _save_raw_json(cfg.raw_weather_dir, target.cell_id, payload)
            records = parse_open_meteo_daily(payload)
            inserted, skipped = _persist_records(repository, target.cell_id, records)
            results.append(
                WeatherIngestResult(
                    cell_id=target.cell_id,
                    fetched=len(records),
                    inserted=inserted,
                    skipped=skipped,
                    raw_path=raw_path,
                )
            )
            logger.info(
                "Clima %s: fetched=%s inserted=%s skipped=%s raw=%s",
                target.cell_id,
                len(records),
                inserted,
                skipped,
                raw_path,
            )
        return results
    finally:
        session.close()
        engine.dispose()


def _ingest_offline(cfg: Settings) -> list[WeatherIngestResult]:
    """Delega para seed de clima quando OFFLINE_MODE esta ativo."""
    counts = load_weather_seed_if_offline(cfg)
    if counts is None:
        return []

    inserted, skipped = counts
    fetched = inserted + skipped
    return [
        WeatherIngestResult(
            cell_id="OFFLINE_SEED",
            fetched=fetched,
            inserted=inserted,
            skipped=skipped,
            raw_path=None,
        )
    ]


def _save_raw_json(raw_dir: Path, cell_id: str, payload: dict) -> Path:
    """Grava snapshot bruto em data/raw/weather/."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_id = cell_id.replace("/", "_")
    path = raw_dir / f"{safe_id}_{stamp}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _persist_records(
    repository: OrbitFireRepository,
    cell_id: str,
    records: list[ParsedWeatherDaily],
) -> tuple[int, int]:
    """Insere registros climaticos com deduplicacao por celula e dia."""
    inserted, skipped = 0, 0
    for record in records:
        result = repository.add_weather_daily(
            cell_id=cell_id,
            day=record.day,
            temp_max=record.temp_max,
            temp_min=record.temp_min,
            precip_mm=record.precip_mm,
            wind_speed=record.wind_speed,
        )
        inserted, skipped = tally_insert(result, inserted, skipped)
    return inserted, skipped


def main() -> None:
    """Entrypoint: python -m src.infrastructure.weather.ingest"""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    results = run_weather_ingest()
    for item in results:
        print(
            f"{item.cell_id}: fetched={item.fetched} "
            f"inserted={item.inserted} skipped={item.skipped}"
        )


if __name__ == "__main__":
    main()
