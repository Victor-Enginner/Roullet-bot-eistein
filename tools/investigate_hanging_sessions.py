"""
Script para investigar sessões não encerradas (bot reiniciado no meio de gale).

Essas sessões podem indicar:
1. Bot reiniciado no meio de um ciclo de aposta
2. Crash do sistema
3. Sessões de teste que nunca foram finalizadas
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path(__file__).parent.parent / 'data' / 'database.sqlite'


def investigate_hanging_sessions():
    """Investiga sessões não encerradas."""
    
    if not DB_PATH.exists():
        print(f"❌ Banco não encontrado: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("🔓 INVESTIGAÇÃO: SESSÕES NÃO ENCERRADAS")
    print("=" * 60)
    
    # 1. Lista todas as sessões não encerradas
    cursor.execute('''
        SELECT id, started_at, numbers_count, errors_count
        FROM sessions 
        WHERE ended_at IS NULL
        ORDER BY started_at DESC
    ''')
    
    hanging = cursor.fetchall()
    print(f"\n📊 Total de sessões não encerradas: {len(hanging)}")
    
    if not hanging:
        print("✅ Nenhuma sessão pendurada!")
        conn.close()
        return
    
    # 2. Detalhes de cada sessão
    print("\n📋 Detalhes das sessões penduradas:")
    for session_id, started_at, numbers_count, errors_count in hanging:
        # Calcular idade da sessão
        start_dt = datetime.strptime(started_at, '%Y-%m-%d %H:%M:%S')
        age = datetime.now() - start_dt
        age_hours = age.total_seconds() / 3600
        
        print(f"\n  Sessão {session_id}:")
        print(f"    Iniciada: {started_at}")
        print(f"    Idade: {age_hours:.1f} horas")
        print(f"    Números: {numbers_count}")
        print(f"    Erros: {errors_count}")
        
        # Verificar se há resultados associados a esta sessão
        cursor.execute('''
            SELECT event_type, COUNT(*) 
            FROM results 
            WHERE session_id = ?
            GROUP BY event_type
        ''', (session_id,))
        
        results = cursor.fetchall()
        if results:
            print(f"    Resultados:")
            for event_type, count in results:
                print(f"      {event_type}: {count}")
        else:
            print(f"    ⚠️  Sem resultados (sessão vazia)")
    
    # 3. Verificar sessões muito antigas (> 24 horas)
    one_day_ago = datetime.now() - timedelta(days=1)
    old_sessions = [s for s in hanging if datetime.strptime(s[1], '%Y-%m-%d %H:%M:%S') < one_day_ago]
    
    print(f"\n⏰ Sessões antigas (> 24 horas): {len(old_sessions)}")
    if old_sessions:
        print("  Recomendação: Fechar essas sessões automaticamente")
    
    # 4. Verificar sessões vazias (0 números)
    empty_sessions = [s for s in hanging if s[2] == 0]
    print(f"\n📭 Sessões vazias (0 números): {len(empty_sessions)}")
    if empty_sessions:
        print("  Recomendação: Essas podem ser deletadas (sessões de teste)")
    
    conn.close()
    print("\n" + "=" * 60)
    print("✅ Investigação concluída")
    print("=" * 60)


if __name__ == '__main__':
    investigate_hanging_sessions()
