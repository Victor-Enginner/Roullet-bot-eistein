from typing import List, Dict, Any, Optional

class MartingaleStrategy:
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

    def _calculate_confidence(self, probability: float, sample_size: int) -> float:
        """Calculate confidence score based on probability and sample size"""
        if sample_size < 10:
            return probability * 0.5  # Low confidence with small sample
        elif sample_size < 50:
            return probability * 0.7
        else:
            return min(probability * 0.9, 0.95)  # Cap at 95%