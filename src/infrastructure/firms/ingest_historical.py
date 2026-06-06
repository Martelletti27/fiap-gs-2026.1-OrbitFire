"""Job de ingestao FIRMS SP (historico) para treino do modelo."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.config import (
    FIRMS_NASA_MAP,
    FIRMS_SOURCES_SP,
    FIRMS_SP_CHUNK_DAYS,
    TRAIN_PERIOD_END,
    TRAIN_PERIOD_START,
    Settings,
    ensure_data_dirs,
    load_settings,
)
from src.domain.firms_windows import iter_firms_date_windows
from src.infrastructure.db.repository import OrbitFireRepository, persist_many, repository_session
from src.infrastructure.firms.client import FirmsAreaClient
from src.infrastructure.firms.ingest import FirmsIngestResult, _persist_events
from src.infrastructure.firms.parser import parse_firms_csv

logger = logging.getLogger(__name__)

FIRMS_HISTORICAL_DELAY_SEC = 1.0


@dataclass(frozen=True)
class FirmsHistoricalSummary:
    """Resumo agregado da ingestao historica SP."""

    windows: int
    fetched: int
    inserted: int
    skipped: int


def run_firms_historical_ingest(
    settings: Settings | None = None,
) -> list[FirmsIngestResult]:
    """Baixa FIRMS SP (jun-set/2024) em janelas de 10 dias e persiste focos."""
    cfg = settings or load_settings()
    ensure_data_dirs(cfg)

    if cfg.offline_mode:
        raise ValueError("Ingestao historica SP requer OFFLINE_MODE=0")

    if not cfg.firms_map_key.strip():
        raise ValueError("FIRMS_MAP_KEY obrigatoria para ingestao historica")

    windows = iter_firms_date_windows(
        TRAIN_PERIOD_START,
        TRAIN_PERIOD_END,
        max_chunk_days=FIRMS_SP_CHUNK_DAYS,
    )
    client = FirmsAreaClient(cfg.firms_map_key)
    results: list[FirmsIngestResult] = []

    with repository_session(cfg.db_path) as repository:
        for logical_source in FIRMS_SOURCES_SP:
            nasa_source = FIRMS_NASA_MAP[logical_source]
            for index, (start_date, day_range) in enumerate(windows):
                if index > 0:
                    time.sleep(FIRMS_HISTORICAL_DELAY_SEC)

                csv_text = client.fetch_area_csv_historical(
                    nasa_source,
                    cfg.bbox,
                    day_range,
                    start_date,
                )
                raw_path = _save_historical_csv(
                    cfg.raw_firms_dir,
                    logical_source,
                    start_date,
                    csv_text,
                )
                events = parse_firms_csv(
                    csv_text,
                    source=logical_source,
                    bbox=cfg.bbox,
                )
                inserted, skipped = _persist_events(repository, events)
                results.append(
                    FirmsIngestResult(
                        source=f"{logical_source}_{start_date.isoformat()}",
                        fetched=len(events),
                        inserted=inserted,
                        skipped=skipped,
                        raw_path=raw_path,
                    )
                )
                logger.info(
                    "FIRMS SP %s desde %s (%sd): fetched=%s inserted=%s skipped=%s",
                    logical_source,
                    start_date,
                    day_range,
                    len(events),
                    inserted,
                    skipped,
                )

    return results


def summarize_historical(results: list[FirmsIngestResult]) -> FirmsHistoricalSummary:
    """Agrega contadores da ingestao historica."""
    return FirmsHistoricalSummary(
        windows=len(results),
        fetched=sum(item.fetched for item in results),
        inserted=sum(item.inserted for item in results),
        skipped=sum(item.skipped for item in results),
    )


def _save_historical_csv(
    raw_dir: Path,
    source: str,
    start_date,
    csv_text: str,
) -> Path:
    """Grava snapshot bruto da janela historica."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = raw_dir / f"{source}_{start_date.isoformat()}_{stamp}.csv"
    path.write_text(csv_text, encoding="utf-8")
    return path


def main() -> None:
    """Entrypoint: python -m src.infrastructure.firms.ingest_historical"""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    results = run_firms_historical_ingest()
    summary = summarize_historical(results)
    print(
        f"FIRMS SP {TRAIN_PERIOD_START}..{TRAIN_PERIOD_END}: "
        f"windows={summary.windows} fetched={summary.fetched} "
        f"inserted={summary.inserted} skipped={summary.skipped}"
    )


if __name__ == "__main__":
    main()
