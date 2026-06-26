from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
import statistics
from collections import Counter

class BaseStrategy(ABC):
    """Base class for all strategy plugins"""

    @abstractmethod
    def analyze(self, current_number: int, history: List[int]) -> Optional[Dict[str, Any]]:
        """
        Analyze current number and history to generate signal

        Returns:
            {
                'signal_type': 'ENTRY' | 'WAIT' | 'STOP',
                'confidence': float (0-1),
                'entry': {'number': int, 'amount': float},
                'gales': int,
                'reason': str
            }
        """
        pass

    def _calculate_confidence(self, probability: float, sample_size: int) -> float:
        """Calculate confidence score based on probability and sample size"""
        if sample_size < 10:
            return probability * 0.5  # Low confidence with small sample
        elif sample_size < 50:
            return probability * 0.7
        else:
            return min(probability * 0.9, 0.95)  # Cap at 95%

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

class ProbabilityStrategy(BaseStrategy):
    """Probability-based strategy using statistical analysis"""

    def analyze(self, current_number: int, history: List[int]) -> Optional[Dict[str, Any]]:
        if len(history) < 20:
            return None

        # Calculate frequency
        counter = Counter(history)
        total = len(history)
        current_freq = counter.get(current_number, 0) / total

        # Expected frequency for fair roulette (36 numbers + 0)
        expected_freq = 1 / 37

        # If below expected, might be due for appearance
        if current_freq < expected_freq * 0.8:
            confidence = min(0.8, (expected_freq - current_freq) / expected_freq)
            return {
                'signal_type': 'ENTRY',
                'confidence': self._calculate_confidence(confidence, total),
                'entry': {'number': current_number, 'amount': 10},
                'gales': 2,
                'reason': f'Number {current_number} below expected frequency'
            }

        return None

class PatternStrategy(BaseStrategy):
    """Pattern recognition strategy"""

    def analyze(self, current_number: int, history: List[int]) -> Optional[Dict[str, Any]]:
        if len(history) < 10:
            return None

        # Look for alternating patterns
        recent = history[-10:]
        alternates = sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])

        if alternates >= 7:  # High alternation
            # Predict opposite of current
            opposite_color = "RED" if self._get_color(current_number) == "BLACK" else "BLACK"
            target_numbers = [n for n in range(1, 37) if self._get_color(n) == opposite_color][:3]

            return {
                'signal_type': 'ENTRY',
                'confidence': self._calculate_confidence(0.7, len(history)),
                'entry': {'numbers': target_numbers, 'amount': 5},
                'gales': 2,
                'reason': 'High alternation pattern detected'
            }

        return None

    def _get_color(self, number: int) -> str:
        """Get number color"""
        if number == 0:
            return "GREEN"
        if 1 <= number <= 10 or 19 <= number <= 28:
            return "RED" if number % 2 == 1 else "BLACK"
        return "BLACK" if number % 2 == 1 else "RED"