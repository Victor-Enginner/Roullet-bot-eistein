"""
Script para investigar a discrepância entre "128/0" relatado vs 262/261/1 no banco.

Possíveis causas:
1. Filtro por estratégia específica
2. Contagem manual de mensagens Telegram vs banco
3. Dashboard frontend mostrando dados diferentes
4. Sessões específicas vs total
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path(__file__).parent.parent / 'data' / 'database.sqlite'


def investigate():
    """Investiga a discrepância de contagem."""
    
    if not DB_PATH.exists():
        print(f"❌ Banco não encontrado: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("🔍 INVESTIGAÇÃO: 128/0 vs 262/261/1")
    print("=" * 60)
    
    # 1. Últimos 7 dias - detalhado
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT event_type, COUNT(*) 
        FROM results 
        WHERE date >= ?
        GROUP BY event_type
    ''', (seven_days_ago,))
    
    print(f"\n📅 Últimos 7 dias (desde {seven_days_ago}):")
    total_7d = 0
    for event_type, count in cursor.fetchall():
        print(f"  {event_type}: {count}")
        total_7d += count
    print(f"  TOTAL: {total_7d}")
    
    # 2. Por estratégia
    cursor.execute('''
        SELECT strategy_name, COUNT(*) 
        FROM results 
        WHERE date >= ?
        GROUP BY strategy_name
        ORDER BY COUNT(*) DESC
    ''', (seven_days_ago,))
    
    print(f"\n🎯 Por estratégia (últimos 7 dias):")
    for strategy, count in cursor.fetchall():
        print(f"  {strategy}: {count}")
    
    # 3. Por sessão
    cursor.execute('''
        SELECT session_id, COUNT(*) 
        FROM results 
        WHERE date >= ?
        GROUP BY session_id
        ORDER BY COUNT(*) DESC
    ''', (seven_days_ago,))
    
    print(f"\n🎲 Por sessão (últimos 7 dias):")
    for session_id, count in cursor.fetchall():
        print(f"  Sessão {session_id}: {count}")
    
    # 4. Últimas 24 horas
    one_day_ago = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT event_type, COUNT(*) 
        FROM results 
        WHERE date >= ?
        GROUP BY event_type
    ''', (one_day_ago,))
    
    print(f"\n⏰ Últimas 24 horas (desde {one_day_ago}):")
    total_24h = 0
    for event_type, count in cursor.fetchall():
        print(f"  {event_type}: {count}")
        total_24h += count
    print(f"  TOTAL: {total_24h}")
    
    # 5. Apenas WIN_ENTRY (entradas reais, sem proteções)
    cursor.execute('''
        SELECT COUNT(*) 
        FROM results 
        WHERE date >= ? AND event_type = 'WIN_ENTRY'
    ''', (seven_days_ago,))
    win_entry_only = cursor.fetchone()[0]
    print(f"\n🎯 Apenas WIN_ENTRY (entradas, sem proteções): {win_entry_only}")
    
    # 6. Verificar se existe alguma estratégia com exatamente 128 entradas
    cursor.execute('''
        SELECT strategy_name, COUNT(*) 
        FROM results 
        GROUP BY strategy_name
        HAVING COUNT(*) = 128
    ''')
    exact_128 = cursor.fetchall()
    if exact_128:
        print(f"\n🎯 Estratégias com exatamente 128 entradas:")
        for strategy, count in exact_128:
            print(f"  {strategy}: {count}")
    else:
        print(f"\n❌ Nenhuma estratégia com exatamente 128 entradas")
    
    # 7. Verificar períodos diferentes
    cursor.execute('''
        SELECT date, COUNT(*) 
        FROM results 
        GROUP BY date
        ORDER BY date DESC
        LIMIT 10
    ''')
    print(f"\n📅 Por dia (últimos 10 dias):")
    for date, count in cursor.fetchall():
        print(f"  {date}: {count}")
    
    conn.close()
    print("\n" + "=" * 60)
    print("✅ Investigação concluída")
    print("=" * 60)


if __name__ == '__main__':
    investigate()
