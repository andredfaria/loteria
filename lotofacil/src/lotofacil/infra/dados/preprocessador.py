"""Feature engineering and dataset preparation for Lotofácil ML."""

import dataclasses
import logging
from datetime import datetime
from typing import List, Tuple

import numpy as np

from lotofacil.infra.config import (
    TOTAL_NUMBERS,
    NUMBERS_PER_DRAW,
    FREQ_WINDOWS,
    LSTM_WINDOW_SIZE,
)

logger = logging.getLogger(__name__)


def _parse_date(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, "%d/%m/%Y")
    except ValueError:
        return datetime(2000, 1, 1)


class LotofacilPreprocessor:
    """Transform a list of draw dicts into ML-ready feature arrays."""

    def __init__(self, draws: list):
        """
        Args:
            draws: sorted list of Draw objects or dicts with "concurso", "data", "dezenas"
        """
        normalized = [d if isinstance(d, dict) else (
            d.model_dump() if hasattr(d, "model_dump") else dataclasses.asdict(d)
        ) for d in draws]
        self.draws = sorted(normalized, key=lambda d: d["concurso"])
        self.n = len(self.draws)

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _binary_matrix(self) -> np.ndarray:
        """Shape (n, 25): 1 if number appeared in draw i."""
        mat = np.zeros((self.n, TOTAL_NUMBERS), dtype=np.float32)
        for i, draw in enumerate(self.draws):
            for d in draw["dezenas"]:
                mat[i, d - 1] = 1.0
        return mat

    def _sliding_frequency(self, binary: np.ndarray, window: int) -> np.ndarray:
        """Frequency of each number in the last `window` draws (per row)."""
        freq = np.zeros_like(binary)
        for i in range(self.n):
            start = max(0, i - window)
            freq[i] = binary[start:i].mean(axis=0) if i > 0 else np.zeros(TOTAL_NUMBERS)
        return freq

    def _days_since_last(self, binary: np.ndarray) -> np.ndarray:
        """For each number, how many draws since it last appeared (shape: n, 25)."""
        result = np.zeros((self.n, TOTAL_NUMBERS), dtype=np.float32)
        last_seen = np.full(TOTAL_NUMBERS, -1, dtype=int)
        for i in range(self.n):
            for j in range(TOTAL_NUMBERS):
                if last_seen[j] < 0:
                    result[i, j] = i  # never seen, use draw index as proxy
                else:
                    result[i, j] = i - last_seen[j]
                if binary[i, j] == 1:
                    last_seen[j] = i
        return result

    def _pattern_features(self) -> np.ndarray:
        """Per-draw scalar features: pares, impares, soma, media, quadrantes (5 cols)."""
        feats = np.zeros((self.n, 5), dtype=np.float32)
        for i, draw in enumerate(self.draws):
            dez = draw["dezenas"]
            pares = sum(1 for d in dez if d % 2 == 0)
            impares = NUMBERS_PER_DRAW - pares
            soma = sum(dez)
            media = soma / NUMBERS_PER_DRAW
            # quadrants: Q1=1-6, Q2=7-12, Q3=13-18, Q4=19-25
            q1 = sum(1 for d in dez if 1 <= d <= 6)
            q2 = sum(1 for d in dez if 7 <= d <= 12)
            q3 = sum(1 for d in dez if 13 <= d <= 18)
            q4 = sum(1 for d in dez if 19 <= d <= 25)
            feats[i] = [pares, impares, soma / 300, media / 25, (q1 + q2 + q3 + q4) / NUMBERS_PER_DRAW]
        return feats

    def _temporal_features(self) -> np.ndarray:
        """Cyclic sin/cos encoding of day-of-week and month (4 cols)."""
        feats = np.zeros((self.n, 4), dtype=np.float32)
        for i, draw in enumerate(self.draws):
            dt = _parse_date(draw["data"])
            dow = dt.weekday()  # 0=Mon
            month = dt.month - 1  # 0-11
            feats[i, 0] = np.sin(2 * np.pi * dow / 7)
            feats[i, 1] = np.cos(2 * np.pi * dow / 7)
            feats[i, 2] = np.sin(2 * np.pi * month / 12)
            feats[i, 3] = np.cos(2 * np.pi * month / 12)
        return feats

    # ── Public API ─────────────────────────────────────────────────────────────

    def prepare_dataset(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Returns:
            X: shape (n-1, features)
            y: shape (n-1, 25)  — whether each number appears in draw i+1
        """
        binary = self._binary_matrix()

        freq_parts = [self._sliding_frequency(binary, w) for w in FREQ_WINDOWS]
        freq_all = self._sliding_frequency(binary, self.n)

        days_since = self._days_since_last(binary)
        # Normalise days_since: cap at 50
        days_since_norm = np.clip(days_since / 50.0, 0, 1)

        patterns = self._pattern_features()
        temporal = self._temporal_features()

        # Broadcast scalar pattern/temporal features to per-number format
        # We replicate the 5+4 scalar features 25 times so X has homogenous shape
        patterns_rep = np.repeat(patterns, TOTAL_NUMBERS, axis=1).reshape(self.n, TOTAL_NUMBERS, -1)
        temporal_rep = np.repeat(temporal, TOTAL_NUMBERS, axis=1).reshape(self.n, TOTAL_NUMBERS, -1)

        # Per-number feature vector: [binary, freq10, freq30, freq100, freq_all, days_since, scalar...]
        # Stack along feature axis: shape (n, 25, n_features_per_num)
        per_num = np.stack([
            binary,
            freq_parts[0],  # freq_10
            freq_parts[1],  # freq_30
            freq_parts[2],  # freq_100
            freq_all,
            days_since_norm,
        ], axis=-1)  # (n, 25, 6)

        # Flatten to (n, 25*6 + 5 + 4)
        flat_per_num = per_num.reshape(self.n, -1)
        X = np.concatenate([flat_per_num, patterns, temporal], axis=1)

        # Target: next draw's binary vector
        y = binary[1:]   # shape (n-1, 25)
        X = X[:-1]       # shape (n-1, features)

        logger.info("Dataset prepared: X=%s y=%s", X.shape, y.shape)
        return X, y

    def prepare_lstm_sequences(self, window_size: int = LSTM_WINDOW_SIZE) -> np.ndarray:
        """
        Returns:
            sequences: shape (n - window_size, window_size, 25)  — binary draw matrix windows
        """
        binary = self._binary_matrix()
        sequences = []
        for i in range(window_size, self.n):
            sequences.append(binary[i - window_size:i])
        arr = np.array(sequences, dtype=np.float32)
        logger.info("LSTM sequences: %s (window=%d)", arr.shape, window_size)
        return arr

    def get_latest_window(self, window_size: int = LSTM_WINDOW_SIZE) -> np.ndarray:
        """Last `window_size` draws as a single LSTM input (1, window, 25)."""
        binary = self._binary_matrix()
        window = binary[-window_size:]
        if len(window) < window_size:
            pad = np.zeros((window_size - len(window), TOTAL_NUMBERS), dtype=np.float32)
            window = np.vstack([pad, window])
        return window[np.newaxis, ...]  # (1, window, 25)

    def get_latest_flat(self) -> np.ndarray:
        """Feature vector for the latest draw (for ML model inference)."""
        X, _ = self.prepare_dataset()
        return X[[-1]]  # (1, features)
