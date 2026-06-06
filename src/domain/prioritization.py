"""Regras puras de priorizacao de celulas para alocacao de brigadas."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.risk_score import RISK_BANDS

# Impulso percentual do score base conforme faixa operacional
BAND_BOOST: dict[str, float] = {
    "baixo": 0.0,
    "medio": 0.05,
    "alto": 0.10,
    "critico": 0.15,
}

FIRE_1D_WEIGHT = 3.0
FIRE_7D_WEIGHT = 1.0
NEIGHBOR_7D_WEIGHT = 0.5
MAX_PRIORITY_SCORE = 100.0

BAND_SEVERITY: dict[str, int] = {band: index for index, band in enumerate(RISK_BANDS)}


@dataclass(frozen=True)
class PrioritizationCandidate:
    """Entrada para ranquear uma celula em um dia de referencia."""

    cell_id: str
    risk_score: float
    band: str
    fires_1d: int = 0
    fires_7d: int = 0
    neighbor_fires_7d: int = 0


@dataclass(frozen=True)
class PrioritizedCell:
    """Celula ranqueada com score composto e posicao."""

    cell_id: str
    priority_score: float
    risk_score: float
    band: str
    rank: int


def compute_priority_score(candidate: PrioritizationCandidate) -> float:
    """Combina risco preditivo com recencia de focos e impulso por faixa."""
    base = max(0.0, min(float(candidate.risk_score), MAX_PRIORITY_SCORE))
    fire_boost = (
        max(0, candidate.fires_1d) * FIRE_1D_WEIGHT
        + max(0, candidate.fires_7d) * FIRE_7D_WEIGHT
        + max(0, candidate.neighbor_fires_7d) * NEIGHBOR_7D_WEIGHT
    )
    band_boost = base * BAND_BOOST.get(candidate.band, 0.0)
    total = base + fire_boost + band_boost
    return round(min(total, MAX_PRIORITY_SCORE), 2)


def rank_priorities(
    candidates: list[PrioritizationCandidate],
    *,
    top_n: int | None = None,
) -> list[PrioritizedCell]:
    """Ordena celulas por prioridade decrescente com desempate deterministico."""
    if not candidates:
        return []
    if top_n is not None and top_n <= 0:
        return []

    scored = [(compute_priority_score(item), item) for item in candidates]
    scored.sort(key=_sort_key)

    limit = len(scored) if top_n is None else min(top_n, len(scored))
    ranked: list[PrioritizedCell] = []
    for index, (priority_score, candidate) in enumerate(scored[:limit], start=1):
        ranked.append(
            PrioritizedCell(
                cell_id=candidate.cell_id,
                priority_score=priority_score,
                risk_score=candidate.risk_score,
                band=candidate.band,
                rank=index,
            )
        )
    return ranked


def build_justification(candidate: PrioritizationCandidate) -> str:
    """Monta justificativa operacional curta em pt-BR para o gestor."""
    parts = [f"Risco preditivo {candidate.risk_score:.0f} (faixa {candidate.band})"]
    if candidate.fires_1d > 0:
        parts.append(f"{candidate.fires_1d} foco(s) na celula nas ultimas 24h")
    if candidate.fires_7d > 0:
        parts.append(f"{candidate.fires_7d} foco(s) na celula em 7 dias")
    if candidate.neighbor_fires_7d > 0:
        parts.append(
            f"{candidate.neighbor_fires_7d} foco(s) em celulas vizinhas em 7 dias"
        )
    return "; ".join(parts) + "."


def _sort_key(item: tuple[float, PrioritizationCandidate]) -> tuple[float, int, float, str]:
    """Chave de ordenacao: prioridade, severidade da faixa, risco, cell_id."""
    priority_score, candidate = item
    severity = BAND_SEVERITY.get(candidate.band, -1)
    return (-priority_score, -severity, -candidate.risk_score, candidate.cell_id)
