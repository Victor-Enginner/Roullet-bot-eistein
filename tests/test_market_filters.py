import unittest
from analytics.market_analysis import analyze_market, check_suspicious_repetition, check_streaks

# --- TEST FIXTURES ---

# Suspicious numbers: 2, 4, 8, 13, 15, 20, 30
SUSPICIOUS = [2, 4, 8, 13, 15, 20, 30]
SAFE_NUMBERS = [1, 3, 5, 7, 9, 10, 11] # Not suspicious

class TestMarketFilters(unittest.TestCase):
    def test_check_streaks_red(self):
        # 5 Reds in a row -> Should return 'RED'
        history = [1, 3, 5, 7, 9] # All Red
        self.assertEqual(check_streaks(history, threshold=5), 'RED')

    def test_check_streaks_clean(self):
        # Alternating -> Should return None
        history = [1, 20, 3, 22, 5] 
        self.assertIsNone(check_streaks(history, threshold=5))

    def test_check_streaks_short(self):
        # Too short -> None
        history = [1, 1, 1]
        self.assertIsNone(check_streaks(history, threshold=5))

    def test_check_suspicious_repetition_safe(self):
        # 20 numbers, mostly safe
        # 3 suspicious numbers out of 20 = 15% (OK)
        history = [1] * 17 + [2, 4, 8]
        self.assertTrue(check_suspicious_repetition(history))

    def test_check_suspicious_repetition_unsafe(self):
        # 20 numbers, 9 suspicious numbers = 45% (> 40%) -> Fail
        # Suspicious: 2, 4, 8, 13, 15, 20, 30
        bad_streak = [2, 4, 8, 13, 15, 20, 30, 2, 4] # 9 numbers
        safe_streak = [1] * 11
        history = safe_streak + bad_streak
        # Total 20. Count suspicious = 9. 9/20 = 0.45.
        self.assertFalse(check_suspicious_repetition(history))

    def test_analyze_market_turbulent_streak(self):
        # Streak of 5 Reds -> Analyze Market should return False
        history = [1, 3, 5, 7, 9] * 4 # A lot of numbers ending in reds
        self.assertFalse(analyze_market([1, 3, 5, 7, 9])["secure"])

    def test_analyze_market_suspicious_flood(self):
        # Recent history with > 40% suspicious numbers
        # 5 safe, 5 suspicious. Total 10. 50% suspicious.
        history = [1, 1, 1, 1, 1, 2, 2, 2, 2, 2]
        self.assertFalse(analyze_market(history)["secure"])

    def test_analyze_market_safe(self):
        # Mixed numbers, no streaks, low suspicious count
        history = [10, 11, 23, 33, 1, 20, 14, 25]
        self.assertTrue(analyze_market(history)["secure"])
