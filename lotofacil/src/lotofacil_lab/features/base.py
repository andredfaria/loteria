"""Base historical features: binary presence, sliding frequency, days-since-last."""

from __future__ import annotations

import numpy as np

from lotofacil_lab.config import TOTAL_NUMBERS

# Feature count per number per timestep
# binary(1) + freq_k5(1) + freq_k10(1) + freq_k30(1) + days_since_norm(1) = 5
N_BASE_PER_NUMBER = 5
N_BASE_FEATURES = TOTAL_NUMBERS * N_BASE_PER_NUMBER  # 125


def binary_matrix(draws) -> np.ndarray:
    """Shape (n, 25): 1 if number appeared in draw i."""
    n = len(draws)
    mat = np.zeros((n, TOTAL_NUMBERS), dtype=np.float32)
    for i, draw in enumerate(draws):
        for d in draw.dezenas:
            mat[i, d - 1] = 1.0
    return mat


def sliding_frequency(binary: np.ndarray, window: int) -> np.ndarray:
    """Mean presence of each number in the last `window` draws (lagged)."""
    n = binary.shape[0]
    freq = np.zeros_like(binary)
    for i in range(n):
        start = max(0, i - window)
        if i > 0:
            freq[i] = binary[start:i].mean(axis=0)
    return freq


def days_since_last(binary: np.ndarray, norm: float = 50.0) -> np.ndarray:
    """Draws since each number last appeared, normalised by `norm`."""
    n, _ = binary.shape
    result = np.zeros_like(binary)
    last_seen = np.full(TOTAL_NUMBERS, -1, dtype=int)

    for i in range(n):
        for j in range(TOTAL_NUMBERS):
            if last_seen[j] < 0:
                result[i, j] = i / norm
            else:
                result[i, j] = (i - last_seen[j]) / norm
            if binary[i, j] == 1:
                last_seen[j] = i
    return np.clip(result, 0.0, 1.0).astype(np.float32)


def build_base_matrix(draws, freq_windows=(5, 10, 30)) -> np.ndarray:
    """Build base feature matrix of shape (n, 125).

    Features per number: binary + freq_k5 + freq_k10 + freq_k30 + days_since
    """
    binary = binary_matrix(draws)
    freq_5 = sliding_frequency(binary, freq_windows[0] if len(freq_windows) > 0 else 5)
    freq_10 = sliding_frequency(binary, freq_windows[1] if len(freq_windows) > 1 else 10)
    freq_30 = sliding_frequency(binary, freq_windows[2] if len(freq_windows) > 2 else 30)
    atraso = days_since_last(binary)

    # Stack per-number, then flatten: shape (n, 25, 5) → (n, 125)
    per_num = np.stack([binary, freq_5, freq_10, freq_30, atraso], axis=-1)
    return per_num.reshape(len(draws), -1).astype(np.float32)


def build_base_sequences(draws, window: int, freq_windows=(5, 10, 30)) -> np.ndarray:
    """Build 3-D base sequences of shape (n - window, window, 125)."""
    binary = binary_matrix(draws)
    freq_5 = sliding_frequency(binary, freq_windows[0] if len(freq_windows) > 0 else 5)
    freq_10 = sliding_frequency(binary, freq_windows[1] if len(freq_windows) > 1 else 10)
    freq_30 = sliding_frequency(binary, freq_windows[2] if len(freq_windows) > 2 else 30)
    atraso = days_since_last(binary)

    per_num = np.stack([binary, freq_5, freq_10, freq_30, atraso], axis=-1)
    flat = per_num.reshape(len(draws), -1)  # (n, 125)

    seqs = []
    for i in range(window, len(draws)):
        seqs.append(flat[i - window:i])
    return np.array(seqs, dtype=np.float32)
