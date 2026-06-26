from typing import List, Dict, Optional
from collections import defaultdict


class TransitionMemory:
    def __init__(self):
        self.transitions: Dict[int, Dict[int, int]] = defaultdict(lambda: defaultdict(int))

    def update(self, history: List[int]) -> None:
        for i in range(len(history) - 1):
            a = history[i]
            b = history[i + 1]
            self.transitions[a][b] += 1

    def get_next_probabilities(self, number: int) -> Dict[int, float]:
        if number not in self.transitions:
            return {}
        followers = self.transitions[number]
        total = sum(followers.values())
        if total == 0:
            return {}
        return {b: count / total for b, count in followers.items()}

    def detect_pattern(self, last_number: int) -> Optional[Dict[int, int]]:
        if last_number not in self.transitions:
            return None
        followers = self.transitions[last_number]
        total = sum(followers.values())
        if total == 0:
            return None
        relevant = {
            b: count
            for b, count in followers.items()
            if count >= 2 and (count / total) >= 0.15
        }
        return relevant if relevant else None
