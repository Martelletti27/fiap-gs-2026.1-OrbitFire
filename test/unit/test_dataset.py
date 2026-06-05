"""Testes do split temporal do dataset (S2.E3)."""

from datetime import date

from src.domain.dataset import temporal_train_test_split


def test_temporal_split_preserves_order() -> None:
    """Dias iniciais vao para treino; finais para teste."""
    days = [date(2026, 6, d) for d in range(1, 11)]
    split = temporal_train_test_split(days, train_ratio=0.8)
    assert len(split.train_days) == 8
    assert len(split.test_days) == 2
    assert date(2026, 6, 1) in split.train_days
    assert date(2026, 6, 10) in split.test_days


def test_temporal_split_single_day_all_train() -> None:
    """Um unico dia fica todo em treino."""
    split = temporal_train_test_split([date(2026, 6, 1)])
    assert split.train_days == frozenset({date(2026, 6, 1)})
    assert split.test_days == frozenset()


def test_temporal_split_empty() -> None:
    """Lista vazia retorna conjuntos vazios."""
    split = temporal_train_test_split([])
    assert len(split.train_days) == 0
    assert len(split.test_days) == 0
