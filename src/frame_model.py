from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List
import re

@dataclass
class FrameModel:
    frame_lexicon: Dict[str, List[str]]

    def score(self, text: str) -> Dict[str, float]:
        t = text.lower()
        scores: Dict[str, float] = {}
        for frame, kws in self.frame_lexicon.items():
            s = 0.0
            for kw in kws:
                kwl = kw.lower()
                if " " in kwl:
                    s += 2.0 * t.count(kwl)
                else:
                    s += len(re.findall(rf"\b{re.escape(kwl)}\b", t))
            scores[frame] = s
        return scores

    def to_state_sequence(self, text: str, window_tokens: int = 220) -> List[str]:
        words = text.split()
        if not words:
            return []
        seq: List[str] = []
        for i in range(0, len(words), window_tokens):
            chunk = " ".join(words[i:i+window_tokens])
            scores = self.score(chunk)
            best = max(scores.items(), key=lambda x: x[1])
            if best[1] <= 0:
                continue
            seq.append(best[0])
        return seq
