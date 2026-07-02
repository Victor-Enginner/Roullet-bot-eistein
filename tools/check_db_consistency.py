"""
Script para verificar consistência do banco de dados e identificar discrepâncias.

Este script ajuda a identificar:
1. Diferença entre contagem do banco e relatórios
2. Linhas com date divergente de detected_at
3. Sessões pendentes (sem WIN/LOSS)
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path(__file__).parent.parent / 'data' / 'database.sqlite'


def check_consistency():
    """Verifica consistência do banco de dados."""
    
    if not DB_PATH.exists():
        print(f"❌ Banco não encontrado: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("📊 VERIFICAÇÃO DE CONSISTÊNCIA DO BANCO")
    print("=" * 60)
    
    # 1. Contagem total de results
    cursor.execute('SELECT COUNT(*) FROM results')
    total_results = cursor.fetchone()[0]
    print(f"\n📈 Total de resultados: {total_results}")
    
    # 2. Contagem por tipo de evento
    cursor.execute('SELECT event_type, COUNT(*) FROM results GROUP BY event_type')
    print("\n📋 Resultados por tipo:")
    for event_type, count in cursor.fetchall():
        print(f"  {event_type}: {count}")
    
    # 3. Verificar divergência de date vs detected_at
    cursor.execute('''
        SELECT COUNT(*) FROM results 
        WHERE date != DATE(detected_at, 'localtime')
    ''')
    divergent = cursor.fetchone()[0]
    print(f"\n⚠️  Linhas com date divergente de detected_at: {divergent}")
    
    if divergent > 0:
        cursor.execute('''
            SELECT id, detected_at, date, DATE(detected_at, 'localtime') as correct_date
            FROM results 
            WHERE date != DATE(detected_at, 'localtime')
            LIMIT 10
        ''')
        print("  Exemplos:")
        for row in cursor.fetchall():
            print(f"    ID {row[0]}: {row[1]} → date={row[2]}, correto={row[3]}")
    
    # 4. Verificar últimos 7 dias
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT COUNT(*) FROM results 
        WHERE date >= ?
    ''', (seven_days_ago,))
    last_7_days = cursor.fetchone()[0]
    print(f"\n📅 Resultados últimos 7 dias (desde {seven_days_ago}): {last_7_days}")
    
    # 5. Contagem por sessão
    cursor.execute('''
        SELECT session_id, COUNT(*) as count 
        FROM results 
        GROUP BY session_id 
        ORDER BY count DESC
        LIMIT 10
    ''')
    print("\n🎯 Top 10 sessões por quantidade de resultados:")
    for session_id, count in cursor.fetchall():
        print(f"  Sessão {session_id}: {count} resultados")
    
    # 6. Verificar sessões sem encerramento
    cursor.execute('''
        SELECT COUNT(*) FROM sessions 
        WHERE ended_at IS NULL
    ''')
    open_sessions = cursor.fetchone()[0]
    print(f"\n🔓 Sessões não encerradas: {open_sessions}")
    
    # 7. Verificar números detectados
    cursor.execute('SELECT COUNT(*) FROM numbers')
    total_numbers = cursor.fetchone()[0]
    print(f"\n🔢 Total de números detectados: {total_numbers}")
    
    # 8. Período dos dados
    cursor.execute('SELECT MIN(detected_at), MAX(detected_at) FROM results')
    min_date, max_date = cursor.fetchone()
    print(f"\n📅 Período dos resultados: {min_date} a {max_date}")
    
    cursor.execute('SELECT MIN(detected_at), MAX(detected_at) FROM numbers')
    min_num, max_num = cursor.fetchone()
    print(f"📅 Período dos números: {min_num} a {max_num}")
    
    conn.close()
    print("\n" + "=" * 60)
    print("✅ Verificação concluída")
    print("=" * 60)


if __name__ == '__main__':
    check_consistency()
