"""Modelos SQLAlchemy das tabelas do OrbitFire."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Index, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarativa para todas as tabelas."""


class GridCell(Base):
    """Celula da grade geografica do Centro-Oeste."""

    __tablename__ = "grid_cells"

    cell_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    lat_center: Mapped[float] = mapped_column(Float, nullable=False)
    lon_center: Mapped[float] = mapped_column(Float, nullable=False)
    uf: Mapped[str | None] = mapped_column(String(2), nullable=True)


class FireEvent(Base):
    """Deteccao individual FIRMS (VIIRS ou MODIS)."""

    __tablename__ = "fire_events"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "acq_datetime",
            "lat",
            "lon",
            name="uq_fire_dedup",
        ),
        Index("ix_fire_acq_datetime", "acq_datetime"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    acq_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    frp: Mapped[float | None] = mapped_column(Float, nullable=True)
    cell_id: Mapped[str | None] = mapped_column(String(32), nullable=True)


class WeatherDaily(Base):
    """Clima diario agregado por celula."""

    __tablename__ = "weather_daily"
    __table_args__ = (
        UniqueConstraint("cell_id", "day", name="uq_weather_cell_day"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cell_id: Mapped[str] = mapped_column(String(32), nullable=False)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    temp_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    temp_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    precip_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_speed: Mapped[float | None] = mapped_column(Float, nullable=True)


class RiskScore(Base):
    """Score preditivo e faixa de risco por celula e data de referencia."""

    __tablename__ = "risk_scores"
    __table_args__ = (
        UniqueConstraint("cell_id", "reference_date", name="uq_risk_cell_date"),
        Index("ix_risk_cell_date", "cell_id", "reference_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cell_id: Mapped[str] = mapped_column(String(32), nullable=False)
    reference_date: Mapped[date] = mapped_column(Date, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    band: Mapped[str] = mapped_column(String(16), nullable=False)
    probability: Mapped[float | None] = mapped_column(Float, nullable=True)
