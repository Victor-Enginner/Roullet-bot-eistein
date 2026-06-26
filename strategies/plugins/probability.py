from typing import List, Dict, Any, Optional
from .base import BaseStrategy

class MartingaleStrategy(BaseStrategy):
    """Martingale-based strategy with reset logic"""

    def analyze(self, current_number: int, history: List[int]) -> Optional[Dict[str, Any]]:
        if len(history) < 5:
            return None

        # Check for sequence patterns
        recent = history[-5:]
        if len(set(recent)) == 1:  # All same number
            return {
                'signal_type': 'ENTRY',
                'confidence': self._calculate_confidence(0.75, len(history)),
                'entry': {'number': recent[0], 'amount': 10},
                'gales': 3,
                'reason': f'Sequence of {recent[0]} detected'
            }

        # Martingale progression
        last_five = history[-5:]
        avg_amount = sum(last_five) / len(last_five)

        return {
            'signal_type': 'ENTRY',
            'confidence': self._calculate_confidence(0.6, len(history)),
            'entry': {'number': current_number, 'amount': max(5, avg_amount)},
            'gales': 3,
            'reason': 'Martingale progression'
        }