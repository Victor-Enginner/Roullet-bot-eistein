import os
from engine.decision_engine import DecisionEngine


def test_martingale_modificada_short_history():
    engine = DecisionEngine(db_path=':memory:')
    assert engine.martingale_modificada([]) == 1
    assert engine.martingale_modificada([1, 5]) == 1
    engine.close()


def test_martingale_modificada_reset_sequence():
    engine = DecisionEngine(db_path=':memory:')
    history = [2, 2, 2]
    assert engine.martingale_modificada(history) == 1
    engine.close()


def test_martingale_modificada_gale_calc():
    engine = DecisionEngine(db_path=':memory:')
    history = [1, 2, 3, 4, 5]
    assert engine.martingale_modificada(history) == 14
    engine.close()


def test_database_log_bet(tmp_path):
    db_path = tmp_path / 'test_skynet.db'
    engine = DecisionEngine(db_path=str(db_path))
    engine.log_bet(number=13, color='RED', strategy='martingale', bet_size=2)

    cursor = engine.db.cursor()
    cursor.execute('SELECT number, color, strategy, bet_size FROM history ORDER BY id DESC LIMIT 1')
    row = cursor.fetchone()
    assert row == (13, 'RED', 'martingale', 2)

    engine.close()
