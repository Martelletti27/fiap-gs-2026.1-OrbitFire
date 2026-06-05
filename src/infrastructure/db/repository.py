"""Sessao SQLite e operacoes basicas de persistencia."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from src.infrastructure.db.schema import Base, FireEvent, GridCell, RiskScore, WeatherDaily


def create_engine_for_db(db_path: Path | None = None, *, memory: bool = False) -> Engine:
    """Cria engine SQLite para arquivo ou memoria (testes)."""
    if memory:
        return create_engine("sqlite:///:memory:")
    if db_path is None:
        raise ValueError("db_path obrigatorio quando memory=False")
    url = f"sqlite:///{db_path.resolve().as_posix()}"
    return create_engine(url, future=True)


def init_db(engine: Engine) -> None:
    """Cria todas as tabelas se ainda nao existirem."""
    Base.metadata.create_all(engine)


@dataclass(frozen=True)
class InsertResult:
    """Resultado de insert com suporte a deduplicacao."""

    inserted: bool
    row_id: int | None = None


class OrbitFireRepository:
    """CRUD basico para as tabelas do POC."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add_grid_cell(
        self,
        cell_id: str,
        lat_center: float,
        lon_center: float,
        uf: str | None = None,
    ) -> InsertResult:
        """Insere celula da grade; ignora se cell_id ja existir."""
        row = GridCell(
            cell_id=cell_id,
            lat_center=lat_center,
            lon_center=lon_center,
            uf=uf,
        )
        return self._persist(row)

    def add_fire_event(
        self,
        source: str,
        acq_datetime: datetime,
        lat: float,
        lon: float,
        confidence: float | None = None,
        frp: float | None = None,
        cell_id: str | None = None,
    ) -> InsertResult:
        """Insere foco FIRMS; dedup por (source, acq_datetime, lat, lon)."""
        row = FireEvent(
            source=source,
            acq_datetime=acq_datetime,
            lat=round(lat, 4),
            lon=round(lon, 4),
            confidence=confidence,
            frp=frp,
            cell_id=cell_id,
        )
        return self._persist(row)

    def add_weather_daily(
        self,
        cell_id: str,
        day: date,
        temp_max: float | None = None,
        temp_min: float | None = None,
        precip_mm: float | None = None,
        wind_speed: float | None = None,
    ) -> InsertResult:
        """Insere registro climatico diario por celula."""
        row = WeatherDaily(
            cell_id=cell_id,
            day=day,
            temp_max=temp_max,
            temp_min=temp_min,
            precip_mm=precip_mm,
            wind_speed=wind_speed,
        )
        return self._persist(row)

    def add_risk_score(
        self,
        cell_id: str,
        reference_date: date,
        score: float,
        band: str,
        probability: float | None = None,
    ) -> InsertResult:
        """Insere score preditivo para celula e data de referencia."""
        row = RiskScore(
            cell_id=cell_id,
            reference_date=reference_date,
            score=score,
            band=band,
            probability=probability,
        )
        return self._persist(row)

    def count_grid_cells(self) -> int:
        """Total de celulas cadastradas."""
        return self._count(GridCell)

    def count_fire_events(self) -> int:
        """Total de focos FIRMS persistidos."""
        return self._count(FireEvent)

    def count_weather_daily(self) -> int:
        """Total de registros climaticos."""
        return self._count(WeatherDaily)

    def count_risk_scores(self) -> int:
        """Total de scores de risco."""
        return self._count(RiskScore)

    def _persist(self, row: Base) -> InsertResult:
        """Tenta insert; retorna inserted=False em violacao de unique."""
        try:
            with self._session.begin_nested():
                self._session.add(row)
                self._session.flush()
            self._session.commit()
            return InsertResult(inserted=True, row_id=getattr(row, "id", None))
        except IntegrityError:
            self._session.rollback()
            return InsertResult(inserted=False)

    def _count(self, model: type[Base]) -> int:
        """Conta linhas de uma tabela."""
        stmt = select(func.count()).select_from(model)
        return int(self._session.scalar(stmt) or 0)


def open_repository(
    db_path: Path | None = None,
    *,
    memory: bool = False,
) -> tuple[OrbitFireRepository, Session, Engine]:
    """Abre engine, cria schema e retorna repositorio com sessao."""
    engine = create_engine_for_db(db_path, memory=memory)
    init_db(engine)
    session = sessionmaker(bind=engine, future=True)()
    return OrbitFireRepository(session), session, engine
