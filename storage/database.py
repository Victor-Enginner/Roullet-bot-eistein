import os
import queue
import sqlite3
import threading
from typing import List, Optional, Tuple

from config.settings import Settings
from utils.logger import setup_logger

logger = setup_logger('database')

_STOP = object()


class Database:
    """
    Banco de dados SQLite para persistir histórico de números.

    OTIMIZAÇÃO DE LATÊNCIA:
    - UMA conexão persistente (antes: abria/fechava conexão a cada chamada).
    - PRAGMA journal_mode=WAL + synchronous=NORMAL: remove o fsync síncrono
      caro em todo commit (que travava o loop no disco) sem risco real de
      perda de dados para este caso de uso.
    - save_number()/save_result()/log_error() agora gravam via fila em uma
      thread de escrita dedicada -> o hot path nunca espera o disco.
    - Leituras continuam síncronas (são raras e ficam fora do loop quente),
      protegidas por um lock compartilhado.
    """

    def __init__(self, db_path=None):
        self.db_path = db_path or str(Settings.DB_PATH)
        os.makedirs('data', exist_ok=True)

        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA busy_timeout=3000")
        self._conn.execute("PRAGMA temp_store=MEMORY")

        self._create_tables()

        # Fila de escrita assíncrona (hot path)
        self._wq: "queue.Queue" = queue.Queue(maxsize=5000)
        self._writer = threading.Thread(target=self._write_loop, daemon=True)
        self._writer.start()

        logger.info(f"Banco de dados (WAL/async) inicializado: {self.db_path}")

    # ------------------------------------------------------------------ #
    # Setup
    # ------------------------------------------------------------------ #
    def _create_tables(self):
        with self._lock:
            cur = self._conn.cursor()
            cur.execute('''CREATE TABLE IF NOT EXISTS numbers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                number INTEGER NOT NULL,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                telegram_sent BOOLEAN DEFAULT 0,
                strategy_text TEXT)''')
            cur.execute('''CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                numbers_count INTEGER DEFAULT 0,
                errors_count INTEGER DEFAULT 0)''')
            cur.execute('''CREATE TABLE IF NOT EXISTS errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_type TEXT NOT NULL,
                error_message TEXT,
                occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            cur.execute('''CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                strategy_name TEXT,
                session_id INTEGER,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date TEXT DEFAULT (DATE('now', 'localtime')))''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_numbers_detected ON numbers(detected_at)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_results_strategy ON results(strategy_name)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_results_event ON results(event_type)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_results_date ON results(date)')
            self._conn.commit()
        logger.info("Tabelas e índices verificados/criados")

    # ------------------------------------------------------------------ #
    # Escrita assíncrona
    # ------------------------------------------------------------------ #
    def _write_loop(self):
        while True:
            item = self._wq.get()
            if item is _STOP:
                self._wq.task_done()
                return
            sql, params = item
            try:
                with self._lock:
                    self._conn.execute(sql, params)
                    self._conn.commit()
            except Exception as e:
                logger.error(f"Erro na escrita assíncrona do DB: {e}")
            finally:
                self._wq.task_done()

    def _enqueue_write(self, sql, params):
        try:
            self._wq.put_nowait((sql, params))
        except queue.Full:
            logger.warning("Fila de escrita do DB cheia — gravação descartada.")

    def flush(self, timeout: float = 5.0):
        """Garante que escritas pendentes foram para o disco (use no shutdown)."""
        import time
        deadline = time.time() + timeout
        while not self._wq.empty() and time.time() < deadline:
            time.sleep(0.02)

    # ------------------------------------------------------------------ #
    # Escritas (hot path -> assíncronas)
    # ------------------------------------------------------------------ #
    def save_number(self, number: int, telegram_sent: bool = False, strategy: Optional[str] = None) -> int:
        """Salva um número detectado (NÃO-BLOQUEANTE)."""
        self._enqueue_write(
            'INSERT INTO numbers (number, telegram_sent, strategy_text) VALUES (?, ?, ?)',
            (number, telegram_sent, strategy),
        )
        return -1  # id não é mais usado no hot path; escrita é diferida

    def save_result(self, event_type: str, strategy_name: str, session_id: int):
        self._enqueue_write(
            'INSERT INTO results (event_type, strategy_name, session_id) VALUES (?, ?, ?)',
            (event_type, strategy_name, session_id),
        )

    def log_error(self, error_type: str, error_message: str):
        self._enqueue_write(
            'INSERT INTO errors (error_type, error_message) VALUES (?, ?)',
            (error_type, error_message),
        )

    # ------------------------------------------------------------------ #
    # Sessões (fora do hot path -> síncrono)
    # ------------------------------------------------------------------ #
    def start_session(self) -> int:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute('INSERT INTO sessions DEFAULT VALUES')
            session_id = cur.lastrowid
            self._conn.commit()
        logger.info(f"Nova sessão iniciada (ID: {session_id})")
        return session_id

    def end_session(self, session_id: int, numbers_count: int, errors_count: int):
        self.flush()  # garante que os números da sessão foram gravados
        with self._lock:
            self._conn.execute(
                'UPDATE sessions SET ended_at = CURRENT_TIMESTAMP, numbers_count = ?, errors_count = ? WHERE id = ?',
                (numbers_count, errors_count, session_id),
            )
            self._conn.commit()
        logger.info(f"Sessão {session_id} finalizada")

    # ------------------------------------------------------------------ #
    # Leituras (síncronas, sob lock)
    # ------------------------------------------------------------------ #
    def get_last_numbers(self, limit: int = 10) -> List[Tuple]:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                'SELECT number, detected_at, telegram_sent FROM numbers ORDER BY detected_at DESC LIMIT ?',
                (limit,),
            )
            return cur.fetchall()

    def get_statistics(self) -> dict:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute('SELECT COUNT(*) FROM numbers')
            total_numbers = cur.fetchone()[0]
            cur.execute('SELECT COUNT(*) FROM sessions')
            total_sessions = cur.fetchone()[0]
            cur.execute('SELECT COUNT(*) FROM errors')
            total_errors = cur.fetchone()[0]
            cur.execute('''SELECT number, COUNT(*) as count FROM numbers
                           GROUP BY number ORDER BY count DESC LIMIT 5''')
            most_common = cur.fetchall()
        return {
            'total_numbers': total_numbers,
            'total_sessions': total_sessions,
            'total_errors': total_errors,
            'most_common': most_common,
        }

    def get_results_by_period(self, start_date: str, end_date: str) -> List[Tuple]:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                '''SELECT event_type, strategy_name, detected_at, date FROM results
                   WHERE date BETWEEN ? AND ? ORDER BY detected_at ASC''',
                (start_date, end_date),
            )
            return cur.fetchall()

    def get_strategy_stats(self, strategy_name: str) -> dict:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                'SELECT event_type, COUNT(*) as count FROM results WHERE strategy_name = ? GROUP BY event_type',
                (strategy_name,),
            )
            counts = {row[0]: row[1] for row in cur.fetchall()}
        win_entry = counts.get('WIN_ENTRY', 0)
        win_protection = counts.get('WIN_PROTECTION', 0)
        losses = counts.get('LOSS', 0)
        total = win_entry + win_protection + losses
        return {
            'total': total,
            'win_entry': win_entry,
            'win_protection': win_protection,
            'losses': losses,
            'win_total': win_entry + win_protection,
        }
