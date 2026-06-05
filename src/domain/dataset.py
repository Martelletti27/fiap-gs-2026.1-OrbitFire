"""Regras puras de montagem e split temporal do dataset."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

DEFAULT_TRAIN_RATIO = 0.8


@dataclass(frozen=True)
class TemporalSplit:
    """Particao temporal por dias ordenados."""

    train_days: frozenset[date]
    test_days: frozenset[date]


def temporal_train_test_split(
    days: list[date],
    train_ratio: float = DEFAULT_TRAIN_RATIO,
) -> TemporalSplit:
    """Separa dias em treino (inicio) e teste (fim) sem embaralhar."""
    ordered = sorted(set(days))
    if not ordered:
        return TemporalSplit(train_days=frozenset(), test_days=frozenset())

    if len(ordered) == 1:
        return TemporalSplit(train_days=frozenset(ordered), test_days=frozenset())

    cut = int(len(ordered) * train_ratio)
    cut = max(1, min(cut, len(ordered) - 1))
    train = frozenset(ordered[:cut])
    test = frozenset(ordered[cut:])
    return TemporalSplit(train_days=train, test_days=test)


def split_name_for_day(day: date, temporal: TemporalSplit) -> str:
    """Retorna 'train' ou 'test' para o dia informado."""
    if day in temporal.train_days:
        return "train"
    return "test"
