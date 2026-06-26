from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import json

from storage.database import Database
from analytics.metrics import Metrics
from config.settings import Settings


class SignalEngine:
    """Signal Intelligence Engine - Core do sistema de sinais"""

    def __init__(self, db: Database):
        self.db = db
        self.metrics = Metrics(start_time=datetime.now().timestamp())

        # Load strategy plugins
        self.strategies = self._load_strategies()

        # Signal confidence thresholds
        self.min_confidence = 0.7  # Minimum confidence for signal generation
        self.high_confidence = 0.85  # High confidence threshold

    def _load_strategies(self) -> Dict[str, Any]:
        """Load strategy plugins dynamically"""
        strategies = {}

        # Import built-in strategies
        try:
            from strategies.plugins.martingale import MartingaleStrategy

            strategies["martingale"] = MartingaleStrategy()
        except ImportError:
            pass

        try:
            from strategies.plugins.probability import ProbabilityStrategy

            strategies["probability"] = ProbabilityStrategy()
        except ImportError:
            pass

        try:
            from strategies.plugins.pattern import PatternStrategy

            strategies["pattern"] = PatternStrategy()
        except ImportError:
            pass

        return strategies

    def process_number(self, number: int) -> Optional[Dict[str, Any]]:
        """
        Process a new number and generate signals

        Args:
            number: The detected number (0-36)

        Returns:
            Signal dict or None if no signal generated
        """
        try:
            # Get recent history for analysis
            history = self.db.get_recent_numbers(50)  # Last 50 numbers
            history_numbers = [h["number"] for h in history]

            # Analyze with all strategies
            signals = []
            for strategy_name, strategy in self.strategies.items():
                try:
                    signal = strategy.analyze(number, history_numbers)
                    if signal and signal.get("confidence", 0) >= self.min_confidence:
                        signals.append({"strategy": strategy_name, **signal})
                except Exception as e:
                    print(f"Strategy {strategy_name} error: {e}")

            # Select best signal
            if signals:
                best_signal = max(signals, key=lambda x: x["confidence"])

                # Generate final signal
                signal_data = self._generate_signal(best_signal, number)

                # Check signal score threshold (75)
                if signal_data.get("signal_score", 0) < 75:
                    return None  # Abort low quality signal

                # Save to database
                self._save_signal(signal_data)

                # Update metrics
                self.metrics.numbers_detected += 1

                return signal_data

            return None

        except Exception as e:
            print(f"Signal processing error: {e}")
            self.metrics.errors_count += 1
            return None

    def _generate_signal(
        self, strategy_signal: Dict[str, Any], number: int
    ) -> Dict[str, Any]:
        """Generate final signal from strategy analysis"""

        confidence = strategy_signal["confidence"]
        risk_level = self._calculate_risk_level(confidence)

        # Calculate strategy winrate (0-1)
        strategy_winrate = self._get_strategy_winrate(strategy_signal["strategy"])

        # Pattern strength (use confidence as proxy, 0-1)
        pattern_strength = confidence

        # Risk inverse (1 - risk_numeric, 0-1)
        risk_numeric = self._get_risk_numeric(risk_level)
        risk_inverse = 1 - risk_numeric

        # Signal score (0-100)
        signal_score = (
            confidence * 0.4
            + strategy_winrate * 0.2
            + pattern_strength * 0.2
            + risk_inverse * 0.2
        ) * 100

        signal = {
            "id": f"sig_{int(datetime.now().timestamp())}_{number}",
            "number": number,
            "signal_type": strategy_signal.get("signal_type", "ENTRY"),
            "strategy": strategy_signal["strategy"],
            "confidence": confidence,
            "risk_level": risk_level,
            "signal_score": signal_score,
            "entry": strategy_signal.get("entry", {}),
            "gales": strategy_signal.get("gales", 3),
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "color": self._get_number_color(number),
                "is_high_confidence": confidence >= self.high_confidence,
            },
        }

        return signal

    def _calculate_risk_level(self, confidence: float) -> str:
        """Calculate risk level based on confidence"""
        if confidence >= 0.9:
            return "LOW"
        elif confidence >= 0.8:
            return "MEDIUM"
        elif confidence >= 0.7:
            return "HIGH"
        else:
            return "VERY_HIGH"

    def _get_risk_numeric(self, risk_level: str) -> float:
        """Convert risk level to numeric value (0-1, higher = riskier)"""
        risk_map = {"LOW": 0.1, "MEDIUM": 0.3, "HIGH": 0.6, "VERY_HIGH": 0.9}
        return risk_map.get(risk_level, 0.5)

    def _get_strategy_winrate(self, strategy_name: str) -> float:
        """Get strategy winrate score (0-1)"""
        try:
            stats = self.db.get_strategy_stats(strategy_name)
            if stats["total"] == 0:
                return 0.5  # Default for new strategies
            accuracy = stats["win_total"] / stats["total"]
            # Adjust for sample size (like in analytics)
            return accuracy * (min(stats["total"], 20) / 20)
        except Exception:
            return 0.5  # Fallback

    def _get_number_color(self, number: int) -> str:
        """Get roulette number color"""
        if number == 0:
            return "GREEN"

        # European roulette pattern
        if 1 <= number <= 10 or 19 <= number <= 28:
            return "RED" if number % 2 == 1 else "BLACK"
        return "BLACK" if number % 2 == 1 else "RED"

    def _save_signal(self, signal: Dict[str, Any]):
        """Save signal to database"""
        try:
            self.db.save_signal(
                signal_type=signal["signal_type"],
                confidence=signal["confidence"],
                entry=json.dumps(signal["entry"]),
                gales=signal["gales"],
                strategy=signal["strategy"],
                result="PENDING",
            )
        except Exception as e:
            print(f"Error saving signal: {e}")

    def get_signal_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent signal history"""
        return self.db.get_recent_signals(limit)

    def get_statistics(self) -> Dict[str, Any]:
        """Get signal engine statistics"""
        return {
            "total_signals": len(self.get_signal_history()),
            "active_strategies": len(self.strategies),
            "uptime_seconds": self.metrics.uptime_seconds(),
            "numbers_processed": self.metrics.numbers_detected,
            "error_rate": self.metrics.errors_count
            / max(1, self.metrics.numbers_detected),
        }
