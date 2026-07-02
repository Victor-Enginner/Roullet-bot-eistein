import sqlite3

conn = sqlite3.connect('data/database.sqlite')
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM results WHERE date >= DATE("now", "-7 days", "localtime")')
print('Últimos 7 dias (localtime):', cursor.fetchone()[0])

cursor.execute('SELECT event_type, COUNT(*) FROM results WHERE date >= DATE("now", "-7 days", "localtime") GROUP BY event_type')
print('Por tipo:')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]}')

conn.close()
