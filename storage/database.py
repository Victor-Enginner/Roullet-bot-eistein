import sqlite3
from datetime import datetime
from typing import List, Optional, Tuple
from config.settings import Settings
from utils.logger import setup_logger

logger = setup_logger('database')

class Database:
    """
    Banco de dados SQLite para persistir histórico de números
    
    Benefícios:
    - Não perde dados em crash
    - Permite análise posterior
    - Detecta números duplicados
    - Rastreabilidade completa
    """
    
    def __init__(self, db_path=None):
        self.db_path = db_path or str(Settings.DB_PATH)
        self._create_tables()
        logger.info(f"Banco de dados inicializado: {self.db_path}")
    
    def _create_tables(self):
        """Cria tabelas se não existirem"""
        import os
        os.makedirs('data', exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS numbers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                number INTEGER NOT NULL,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                telegram_sent BOOLEAN DEFAULT 0,
                strategy_text TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                numbers_count INTEGER DEFAULT 0,
                errors_count INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_type TEXT NOT NULL,
                error_message TEXT,
                occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL, -- 'WIN_ENTRY', 'WIN_PROTECTION', 'LOSS'
                strategy_name TEXT,
                session_id INTEGER,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date TEXT DEFAULT (DATE('now', 'localtime')) -- YYYY-MM-DD
            )
        ''')

        # --- ÍNDICES DE PERFORMANCE (MELHORIA) ---
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_numbers_detected ON numbers(detected_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_results_strategy ON results(strategy_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_results_event ON results(event_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_results_date ON results(date)')
        
        conn.commit()
        conn.close()
        logger.info("Tabelas e índices do banco de dados verificados/criados")
    
    def save_number(self, number: int, telegram_sent: bool = False, strategy: Optional[str] = None) -> int:
        """Salva um número detectado"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO numbers (number, telegram_sent, strategy_text)
            VALUES (?, ?, ?)
        ''', (number, telegram_sent, strategy))
        
        number_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.debug(f"Número {number} salvo no banco (ID: {number_id})")
        return number_id
    
    def start_session(self) -> int:
        """Inicia uma nova sessão"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('INSERT INTO sessions DEFAULT VALUES')
        session_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        logger.info(f"Nova sessão iniciada (ID: {session_id})")
        return session_id
    
    def end_session(self, session_id: int, numbers_count: int, errors_count: int):
        """Finaliza uma sessão"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE sessions 
            SET ended_at = CURRENT_TIMESTAMP,
                numbers_count = ?,
                errors_count = ?
            WHERE id = ?
        ''', (numbers_count, errors_count, session_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Sessão {session_id} finalizada")
    
    def log_error(self, error_type: str, error_message: str):
        """Registra um erro"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO errors (error_type, error_message)
            VALUES (?, ?)
        ''', (error_type, error_message))
        
        conn.commit()
        conn.close()
        
        logger.debug(f"Erro registrado: {error_type}")
    
    def get_last_numbers(self, limit: int = 10) -> List[Tuple]:
        """Retorna os últimos N números"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT number, detected_at, telegram_sent
            FROM numbers
            ORDER BY detected_at DESC
            LIMIT ?
        ''', (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def get_statistics(self) -> dict:
        """Retorna estatísticas gerais"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM numbers')
        total_numbers = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM sessions')
        total_sessions = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM errors')
        total_errors = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT number, COUNT(*) as count
            FROM numbers
            GROUP BY number
            ORDER BY count DESC
            LIMIT 5
        ''')
        most_common = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_numbers': total_numbers,
            'total_sessions': total_sessions,
            'total_errors': total_errors,
            'most_common': most_common
        }

    def save_result(self, event_type: str, strategy_name: str, session_id: int):
        """Salva um resultado (Green/Red) para persistência global"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO results (event_type, strategy_name, session_id)
            VALUES (?, ?, ?)
        ''', (event_type, strategy_name, session_id))
        
        conn.commit()
        conn.close()
        logger.debug(f"Resultado {event_type} da estratégia {strategy_name} salvo (Sessão: {session_id})")

    def get_results_by_period(self, start_date: str, end_date: str) -> List[Tuple]:
        """Busca resultados no intervalo de datas (inclusive)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT event_type, strategy_name, detected_at, date
            FROM results
            WHERE date BETWEEN ? AND ?
            ORDER BY detected_at ASC
        ''', (start_date, end_date))
        
        results = cursor.fetchall()
        conn.close()
        return results

    def get_strategy_stats(self, strategy_name: str) -> dict:
        """Retorna estatísticas históricas de uma estratégia específica"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT event_type, COUNT(*) as count
            FROM results
            WHERE strategy_name = ?
            GROUP BY event_type
        ''', (strategy_name,))
        
        counts = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        
        win_entry = counts.get('WIN_ENTRY', 0)
        win_protection = counts.get('WIN_PROTECTION', 0)
        losses = counts.get('LOSS', 0)
        total = win_entry + win_protection + losses
        
        return {
            'total': total,
            'win_entry': win_entry,
            'win_protection': win_protection,
            'losses': losses,
            'win_total': win_entry + win_protection
        }
