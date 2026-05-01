"""Evaluation module: metrics, backtest and comparison."""

from evaluation.metrics import mean_hits, hit_rate_at, roi
from evaluation.backtest import BacktestEngine
from evaluation.comparison import compare_approaches
