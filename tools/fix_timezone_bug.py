"""
Script de migração para corrigir bug de fuso horário no banco de dados.

Problema: A coluna 'date' da tabela 'results' usava DEFAULT (DATE('now','localtime'))
no INSERT, o que causava eventos entre 00h-03h a serem gravados no dia anterior.

Solução: 
1. Remover o DEFAULT automático do schema (já feito em storage/database.py)
2. Calcular 'date' explicitamente a partir de 'detected_at' (já feito em storage/database.py)
3. Este script corrige os dados históricos já divergentes

Executar: python tools/fix_timezone_bug.py
"""

import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'data' / 'database.sqlite'


def fix_timezone_bug():
    """Corrige as datas divergentes recalculando a partir de detected_at."""
    
    if not DB_PATH.exists():
        print(f"❌ Banco não encontrado: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Backup antes da migração
    backup_path = DB_PATH.parent / f"database_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite"
    import shutil
    shutil.copy2(DB_PATH, backup_path)
    print(f"✅ Backup criado: {backup_path}")
    
    # Verificar quantas linhas estão divergentes
    cursor.execute('''
        SELECT COUNT(*) FROM results 
        WHERE date != DATE(detected_at, 'localtime')
    ''')
    divergent_count = cursor.fetchone()[0]
    print(f"📊 Linhas divergentes encontradas: {divergent_count}")
    
    if divergent_count == 0:
        print("✅ Nenhuma linha divergente encontrada. Nada a corrigir.")
        conn.close()
        return
    
    # Mostrar alguns exemplos antes de corrigir
    cursor.execute('''
        SELECT id, detected_at, date, DATE(detected_at, 'localtime') as correct_date
        FROM results 
        WHERE date != DATE(detected_at, 'localtime')
        LIMIT 5
    ''')
    print("\n📋 Exemplos de divergências:")
    for row in cursor.fetchall():
        print(f"  ID {row[0]}: detected_at={row[1]}, date_atual={row[2]}, date_correto={row[3]}")
    
    # Corrigir todas as linhas divergentes
    print("\n🔧 Corrigindo linhas divergentes...")
    cursor.execute('''
        UPDATE results 
        SET date = DATE(detected_at, 'localtime')
        WHERE date != DATE(detected_at, 'localtime')
    ''')
    conn.commit()
    
    # Verificar resultado
    cursor.execute('''
        SELECT COUNT(*) FROM results 
        WHERE date != DATE(detected_at, 'localtime')
    ''')
    remaining = cursor.fetchone()[0]
    
    print(f"✅ Correção concluída! Linhas restantes divergentes: {remaining}")
    
    conn.close()
    print("\n🎉 Migração concluída com sucesso!")


if __name__ == '__main__':
    fix_timezone_bug()
