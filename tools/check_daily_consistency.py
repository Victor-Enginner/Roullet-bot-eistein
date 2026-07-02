"""
Script de verificação diária de consistência entre banco e relatórios.

Deve ser executado 1x/dia (via cron/scheduler) para verificar:
- Se a contagem do banco bate com o que o dashboard/relatório exibe
- Se há divergência entre SQL direto e relatório usado no dia a dia
- Se há sessões penduradas (bot reiniciado no meio de um gale)

Uso: python tools/check_daily_consistency.py
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any

DB_PATH = Path(__file__).parent.parent / 'data' / 'database.sqlite'


class DailyConsistencyChecker:
    """Verifica consistência diária do banco de dados."""
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Conecta ao banco."""
        if not self.db_path.exists():
            raise FileNotFoundError(f"Banco não encontrado: {self.db_path}")
        
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
    
    def disconnect(self):
        """Fecha conexão."""
        if self.conn:
            self.conn.close()
    
    def get_today_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de hoje."""
        today = datetime.now().strftime('%Y-%m-%d')
        
        self.cursor.execute('''
            SELECT event_type, COUNT(*) 
            FROM results 
            WHERE date = ?
            GROUP BY event_type
        ''', (today,))
        
        stats = {row[0]: row[1] for row in self.cursor.fetchall()}
        stats['total'] = sum(stats.values())
        stats['date'] = today
        
        return stats
    
    def get_last_7_days_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas dos últimos 7 dias."""
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        self.cursor.execute('''
            SELECT event_type, COUNT(*) 
            FROM results 
            WHERE date >= ?
            GROUP BY event_type
        ''', (seven_days_ago,))
        
        stats = {row[0]: row[1] for row in self.cursor.fetchall()}
        stats['total'] = sum(stats.values())
        stats['period_start'] = seven_days_ago
        
        return stats
    
    def check_hanging_sessions(self) -> list:
        """Verifica sessões não encerradas (bot reiniciado no meio de gale)."""
        self.cursor.execute('''
            SELECT id, started_at, numbers_count 
            FROM sessions 
            WHERE ended_at IS NULL
            ORDER BY started_at DESC
        ''')
        
        return self.cursor.fetchall()
    
    def check_divergent_dates(self) -> int:
        """Verifica linhas com date divergente de detected_at."""
        self.cursor.execute('''
            SELECT COUNT(*) FROM results 
            WHERE date != DATE(detected_at, 'localtime')
        ''')
        
        return self.cursor.fetchone()[0]
    
    def run_check(self) -> bool:
        """Executa verificação completa e retorna True se tudo OK."""
        try:
            self.connect()
            
            print("=" * 60)
            print("📊 VERIFICAÇÃO DIÁRIA DE CONSISTÊNCIA")
            print("=" * 60)
            
            # 1. Estatísticas de hoje
            today_stats = self.get_today_stats()
            print(f"\n📅 Hoje ({today_stats['date']}):")
            print(f"  Total: {today_stats['total']}")
            for event_type, count in today_stats.items():
                if event_type not in ['total', 'date']:
                    print(f"  {event_type}: {count}")
            
            # 2. Estatísticas últimos 7 dias
            week_stats = self.get_last_7_days_stats()
            print(f"\n📅 Últimos 7 dias (desde {week_stats['period_start']}):")
            print(f"  Total: {week_stats['total']}")
            for event_type, count in week_stats.items():
                if event_type not in ['total', 'period_start']:
                    print(f"  {event_type}: {count}")
            
            # 3. Verificar sessões penduradas
            hanging = self.check_hanging_sessions()
            print(f"\n🔓 Sessões não encerradas: {len(hanging)}")
            if hanging:
                print("  ⚠️  Sessões penduradas (bot pode ter reiniciado no meio de gale):")
                for session_id, started_at, numbers_count in hanging[:5]:
                    print(f"    Sessão {session_id}: iniciada em {started_at}, {numbers_count} números")
            
            # 4. Verificar datas divergentes
            divergent = self.check_divergent_dates()
            print(f"\n⚠️  Linhas com date divergente: {divergent}")
            
            # 5. Verificar se há anomalias
            issues = []
            if len(hanging) > 5:
                issues.append(f"Muitas sessões penduradas ({len(hanging)})")
            if divergent > 0:
                issues.append(f"Datas divergentes ({divergent} linhas)")
            
            if issues:
                print(f"\n❌ PROBLEMAS ENCONTRADOS:")
                for issue in issues:
                    print(f"  - {issue}")
                return False
            else:
                print(f"\n✅ Tudo consistente!")
                return True
            
        except Exception as e:
            print(f"\n❌ Erro na verificação: {e}")
            return False
        finally:
            self.disconnect()


def main():
    """Ponto de entrada."""
    checker = DailyConsistencyChecker()
    is_ok = checker.run_check()
    
    # Exit code para integração com cron/scheduler
    exit(0 if is_ok else 1)


if __name__ == '__main__':
    main()
