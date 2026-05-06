"""Preprocessor: transform draws into ML-ready feature arrays."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Tuple

import numpy as np

from core.config import TOTAL_NUMBERS, NUMBERS_PER_DRAW, FREQ_WINDOWS, LSTM_WINDOW_SIZE
from core.models import Draw
from data.climate_loader import load_all_climate, normalize_climate, get_or_fetch_climate

logger = logging.getLogger(__name__)


def _parse_date(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, "%d/%m/%Y")
    except ValueError:
        return datetime(2000, 1, 1)


def _to_iso_date(date_str: str) -> str:
    """Convert DD/MM/YYYY to YYYY-MM-DD, or return empty string on failure."""
    try:
        return datetime.strptime(date_str.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return ""


class LotofacilPreprocessor:
    """Transform a list of Draw objects into ML-ready feature arrays."""

    def __init__(self, draws: list[Draw]):
        self.draws = sorted(draws, key=lambda d: d.concurso)
        self.n = len(self.draws)
        self._climate_map = load_all_climate()

    def _binary_matrix(self) -> np.ndarray:
        """Shape (n, 25): 1 if number appeared in draw i."""
        mat = np.zeros((self.n, TOTAL_NUMBERS), dtype=np.float32)
        for i, draw in enumerate(self.draws):
            for d in draw.dezenas:
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
        """For each number, how many draws since it last appeared."""
        result = np.zeros((self.n, TOTAL_NUMBERS), dtype=np.float32)
        last_seen = np.full(TOTAL_NUMBERS, -1, dtype=int)
        for i in range(self.n):
            for j in range(TOTAL_NUMBERS):
                if last_seen[j] < 0:
                    result[i, j] = i
                else:
                    result[i, j] = i - last_seen[j]
                if binary[i, j] == 1:
                    last_seen[j] = i
        return result

    def _pattern_features(self) -> np.ndarray:
        """Per-draw scalar features: pares, impares, soma, media, quadrantes."""
        feats = np.zeros((self.n, 5), dtype=np.float32)
        for i, draw in enumerate(self.draws):
            dez = draw.dezenas
            pares = sum(1 for d in dez if d % 2 == 0)
            impares = NUMBERS_PER_DRAW - pares
            soma = sum(dez)
            media = soma / NUMBERS_PER_DRAW
            q1 = sum(1 for d in dez if 1 <= d <= 6)
            q2 = sum(1 for d in dez if 7 <= d <= 12)
            q3 = sum(1 for d in dez if 13 <= d <= 18)
            q4 = sum(1 for d in dez if 19 <= d <= 25)
            feats[i] = [pares, impares, soma / 300, media / 25, (q1 + q2 + q3 + q4) / NUMBERS_PER_DRAW]
        return feats

    def _temporal_features(self) -> np.ndarray:
        """Cyclic sin/cos encoding of day-of-week and month."""
        feats = np.zeros((self.n, 4), dtype=np.float32)
        for i, draw in enumerate(self.draws):
            dt = _parse_date(draw.data)
            dow = dt.weekday()
            month = dt.month - 1
            feats[i, 0] = np.sin(2 * np.pi * dow / 7)
            feats[i, 1] = np.cos(2 * np.pi * dow / 7)
            feats[i, 2] = np.sin(2 * np.pi * month / 12)
            feats[i, 3] = np.cos(2 * np.pi * month / 12)
        return feats

    def _climate_features(self) -> np.ndarray:
        """Per-draw climate features, shape (n, 8).

        Features per draw:
            temp_min, temp_max, temp_media, temp_sorteio (normalized /40)
            precip_media, precip_sorteio (normalized /100)
            wcode_sorteio, wcode_dominant (normalized /99)

        Missing climate data → fetches from Open-Meteo API and saves locally.
        If API also fails → zeros (graceful degradation).
        """
        feats = np.zeros((self.n, 8), dtype=np.float32)
        for i, draw in enumerate(self.draws):
            if draw.concurso in self._climate_map:
                resumo = self._climate_map[draw.concurso]
                feats[i] = normalize_climate(resumo)
                continue

            date_iso = _to_iso_date(draw.data)
            if not date_iso:
                continue

            resumo = get_or_fetch_climate(draw.concurso, date_iso)
            if resumo:
                self._climate_map[draw.concurso] = resumo
                feats[i] = normalize_climate(resumo)
            else:
                logger.warning("No climate data for concurso %s (%s), using zeros",
                               draw.concurso, date_iso)

        return feats

    def prepare_dataset(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Returns:
            X: shape (n-1, features)
            y: shape (n-1, 25) — whether each number appears in draw i+1
        """
        binary = self._binary_matrix()
        freq_parts = [self._sliding_frequency(binary, w) for w in FREQ_WINDOWS]
        freq_all = self._sliding_frequency(binary, self.n)
        days_since = self._days_since_last(binary)
        days_since_norm = np.clip(days_since / 50.0, 0, 1)
        patterns = self._pattern_features()
        temporal = self._temporal_features()

        patterns_rep = np.repeat(patterns, TOTAL_NUMBERS, axis=1).reshape(self.n, TOTAL_NUMBERS, -1)
        temporal_rep = np.repeat(temporal, TOTAL_NUMBERS, axis=1).reshape(self.n, TOTAL_NUMBERS, -1)

        per_num = np.stack([
            binary,
            freq_parts[0],
            freq_parts[1],
            freq_parts[2],
            freq_all,
            days_since_norm,
        ], axis=-1)

        flat_per_num = per_num.reshape(self.n, -1)
        X = np.concatenate([flat_per_num, patterns, temporal], axis=1)
        y = binary[1:]
        X = X[:-1]

        logger.info("Dataset prepared: X=%s y=%s", X.shape, y.shape)
        return X, y

    def prepare_lstm_sequences(self, window_size: int = LSTM_WINDOW_SIZE) -> np.ndarray:
        """
        Returns:
            sequences: shape (n - window_size, window_size, 25)
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
        return window[np.newaxis, ...]

    def get_latest_flat(self) -> np.ndarray:
        """Feature vector for the latest draw (for ML model inference)."""
        X, _ = self.prepare_dataset()
        return X[[-1]]

    def prepare_enriched_sequences(self, window_size: int = LSTM_WINDOW_SIZE):
        """
        Build enriched sequences: binary matrix + freq features per draw.

        Returns:
            X: (n - window_size, window_size, 25) binary draws
            y: (n - window_size, 25) next draw binary
            freq: (n - window_size, window_size, 25) sliding frequency
            atraso: (n - window_size, 25) delay features
            climate: (n - window_size, window_size, 8) climate features
        """
        binary = self._binary_matrix()
        freq = self._sliding_frequency(binary, 10)
        days_since = self._days_since_last(binary)
        atraso_norm = np.clip(days_since / 20.0, 0, 1)
        climate = self._climate_features()

        X_seq, y_seq, f_seq, a_seq, c_seq = [], [], [], [], []
        for i in range(window_size, self.n):
            X_seq.append(binary[i - window_size:i])
            y_seq.append(binary[i])
            f_seq.append(freq[i - window_size:i])
            a_seq.append(atraso_norm[i])
            c_seq.append(climate[i - window_size:i])

        X_arr = np.array(X_seq, dtype=np.float32)
        y_arr = np.array(y_seq, dtype=np.float32)
        f_arr = np.array(f_seq, dtype=np.float32)
        a_arr = np.array(a_seq, dtype=np.float32)
        c_arr = np.array(c_seq, dtype=np.float32)

        logger.info("Enriched sequences: X=%s y=%s freq=%s atraso=%s climate=%s",
                     X_arr.shape, y_arr.shape, f_arr.shape, a_arr.shape, c_arr.shape)
        return X_arr, y_arr, f_arr, a_arr, c_arr

    def prepare_advanced_sequences(self, window_size: int = LSTM_WINDOW_SIZE):
        """
        Build advanced feature sequences with cycle patterns, quadrant distribution,
        and heatmap features.

        Returns:
            X: (n - window_size, window_size, 100) enriched feature tensor
            y: (n - window_size, 25) next draw binary

        Features per number (4 per number = 100 total):
        - Cycle pattern: appeared in last 1, 3, 5, 10 draws (4 features)
        - Quadrant membership (4 features, one-hot)
        - Heatmap intensity: exponential decay of appearances over last 20 draws (25 features shared)
        - Original binary + freq + delay (25*3 = 75 features)
        """
        binary = self._binary_matrix()
        freq = self._sliding_frequency(binary, 10)
        days_since = self._days_since_last(binary)
        atraso_norm = np.clip(days_since / 20.0, 0, 1)

        # Cycle features: for each number, binary flags for appearing in last N draws
        cycle_features = np.zeros((self.n, TOTAL_NUMBERS, 4), dtype=np.float32)
        for i in range(self.n):
            for w_idx, window in enumerate([1, 3, 5, 10]):
                start = max(0, i - window)
                cycle_features[i, :, w_idx] = binary[start:i].max(axis=0) if i > start else np.zeros(TOTAL_NUMBERS)

        # Quadrant features: one-hot encoding of which quadrant each number belongs to
        quadrant_map = np.zeros((TOTAL_NUMBERS, 4), dtype=np.float32)
        for num in range(1, 26):
            if num <= 6:
                quadrant_map[num - 1, 0] = 1.0
            elif num <= 12:
                quadrant_map[num - 1, 1] = 1.0
            elif num <= 18:
                quadrant_map[num - 1, 2] = 1.0
            else:
                quadrant_map[num - 1, 3] = 1.0

        # Heatmap: exponential decay of recent appearances
        heatmap = np.zeros((self.n, TOTAL_NUMBERS), dtype=np.float32)
        decay_rate = 0.15
        for i in range(self.n):
            lookback = min(20, i)
            for t in range(lookback):
                decay = np.exp(-decay_rate * t)
                heatmap[i] += binary[i - t - 1] * decay

        X_seq, y_seq, adv_seq = [], [], []
        for i in range(window_size, self.n):
            # Build per-number features: binary(25) + freq(25) + delay(25) + cycle(25*4=100) + quadrant(25*4=100)
            # For efficiency, we concatenate per-timestep:
            # binary(25) + freq(25) + atraso(25) + cycle(25) + heatmap(25) = 125 per timestep
            window_binary = binary[i - window_size:i]  # (window, 25)
            window_freq = freq[i - window_size:i]  # (window, 25)
            window_cycle_max = np.zeros((window_size, TOTAL_NUMBERS), dtype=np.float32)
            for w in range(window_size):
                abs_idx = i - window_size + w
                window_cycle_max[w] = cycle_features[abs_idx].max(axis=1)  # max across cycle windows

            window_heatmap = heatmap[i - window_size:i]  # (window, 25)

            # For each timestep: binary + freq + atraso + cycle_active + heatmap = 25*5 = 125
            combined = np.concatenate([
                window_binary,
                window_freq,
                atraso_norm[i - window_size:i],
                window_cycle_max,
                window_heatmap,
            ], axis=-1)

            X_seq.append(combined)
            y_seq.append(binary[i])
            adv_seq.append(combined)

        X_arr = np.array(X_seq, dtype=np.float32)
        y_arr = np.array(y_seq, dtype=np.float32)

        logger.info("Advanced sequences: X=%s y=%s features_per_timestep=%d",
                     X_arr.shape, y_arr.shape, X_arr.shape[2])
        return X_arr, y_arr
