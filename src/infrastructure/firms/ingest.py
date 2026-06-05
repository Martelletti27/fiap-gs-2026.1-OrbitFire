"""Job de ingestao FIRMS: API NASA ou seed offline."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.config import FIRMS_DAY_RANGE, FIRMS_NASA_MAP, Settings, ensure_data_dirs, load_settings
from src.infrastructure.db.repository import OrbitFireRepository, open_repository, tally_insert
from src.infrastructure.firms.client import FirmsAreaClient
from src.infrastructure.firms.parser import ParsedFireEvent, parse_firms_csv
from src.infrastructure.seed.loader import load_seed_if_offline

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FirmsIngestResult:
    """Resumo da ingestao por fonte logica ou modo offline."""

    source: str
    fetched: int
    inserted: int
    skipped: int
    raw_path: Path | None = None


def run_firms_ingest(settings: Settings | None = None) -> list[FirmsIngestResult]:
    """Executa ingestao FIRMS conforme OFFLINE_MODE e persiste em fire_events."""
    cfg = settings or load_settings()
    ensure_data_dirs(cfg)

    if cfg.offline_mode:
        return _ingest_offline(cfg)

    if not cfg.firms_map_key.strip():
        raise ValueError("FIRMS_MAP_KEY obrigatoria quando OFFLINE_MODE=0")

    client = FirmsAreaClient(cfg.firms_map_key)
    repository, session, engine = open_repository(cfg.db_path)
    try:
        results: list[FirmsIngestResult] = []
        for logical_source in cfg.firms_sources:
            nasa_source = FIRMS_NASA_MAP[logical_source]
            csv_text = client.fetch_area_csv(nasa_source, cfg.bbox, FIRMS_DAY_RANGE)
            raw_path = _save_raw_csv(cfg.raw_firms_dir, logical_source, csv_text)
            events = parse_firms_csv(csv_text, source=logical_source, bbox=cfg.bbox)
            inserted, skipped = _persist_events(repository, events)
            results.append(
                FirmsIngestResult(
                    source=logical_source,
                    fetched=len(events),
                    inserted=inserted,
                    skipped=skipped,
                    raw_path=raw_path,
                )
            )
            logger.info(
                "FIRMS %s: fetched=%s inserted=%s skipped=%s raw=%s",
                logical_source,
                len(events),
                inserted,
                skipped,
                raw_path,
            )
        return results
    finally:
        session.close()
        engine.dispose()


def _ingest_offline(cfg: Settings) -> list[FirmsIngestResult]:
    """Delega para seed quando OFFLINE_MODE esta ativo."""
    seed_result = load_seed_if_offline(cfg)
    if seed_result is None:
        return []

    fetched = seed_result.fires_inserted + seed_result.fires_skipped
    return [
        FirmsIngestResult(
            source="OFFLINE_SEED",
            fetched=fetched,
            inserted=seed_result.fires_inserted,
            skipped=seed_result.fires_skipped,
            raw_path=None,
        )
    ]


def _save_raw_csv(raw_dir: Path, source: str, csv_text: str) -> Path:
    """Grava snapshot bruto em data/raw/firms/."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = raw_dir / f"{source}_{stamp}.csv"
    path.write_text(csv_text, encoding="utf-8")
    return path


def _persist_events(
    repository: OrbitFireRepository,
    events: list[ParsedFireEvent],
) -> tuple[int, int]:
    """Insere eventos com deduplicacao via repositorio."""
    inserted, skipped = 0, 0
    for event in events:
        result = repository.add_fire_event(
            source=event.source,
            acq_datetime=event.acq_datetime,
            lat=event.lat,
            lon=event.lon,
            confidence=event.confidence,
            frp=event.frp,
        )
        inserted, skipped = tally_insert(result, inserted, skipped)
    return inserted, skipped


def main() -> None:
    """Entrypoint: python -m src.infrastructure.firms.ingest"""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    results = run_firms_ingest()
    for item in results:
        print(
            f"{item.source}: fetched={item.fetched} "
            f"inserted={item.inserted} skipped={item.skipped}"
        )


if __name__ == "__main__":
    main()
