from __future__ import annotations
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class MarkovResult:
    states: List[str]
    counts: np.ndarray
    P: np.ndarray

def build_markov(seqs: List[List[str]], states: List[str]) -> MarkovResult:
    idx = {s:i for i,s in enumerate(states)}
    n = len(states)
    counts = np.zeros((n,n), dtype=np.int64)
    for seq in seqs:
        for a, b in zip(seq, seq[1:]):
            if a in idx and b in idx:
                counts[idx[a], idx[b]] += 1
    sm = counts + 1
    P = sm / sm.sum(axis=1, keepdims=True)
    return MarkovResult(states=states, counts=counts, P=P)

def entropy_rows(P: np.ndarray) -> np.ndarray:
    eps = 1e-12
    Q = np.clip(P, eps, 1.0)
    return -(Q * np.log(Q)).sum(axis=1)

def loop_strength(P: np.ndarray) -> np.ndarray:
    return np.diag(P)

def kl_divergence(P: np.ndarray, Q: np.ndarray) -> float:
    eps = 1e-12
    P2 = np.clip(P, eps, 1.0)
    Q2 = np.clip(Q, eps, 1.0)
    return float((P2 * (np.log(P2) - np.log(Q2))).sum())
