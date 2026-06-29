"""
numeros_fixos.py — Existe um conjunto FIXO de números sempre quentes?

Testa a crença "16 números que SEMPRE saem muito" medindo PERSISTÊNCIA:
se os mais quentes de um período continuam sendo os mais quentes de outro.
- Persistem  -> viés real (os fixos existem).
- Embaralham -> variância (não há conjunto fixo).

Lê direto do BANCO do bot (histórico acumulado).
Uso:
  python tools/numeros_fixos.py            # usa o banco do bot
  python tools/numeros_fixos.py nums.txt   # usa um arquivo de números
"""
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.getcwd())

TOP = 16


def carregar(arg=None):
    if arg:
        txt = open(arg, encoding="utf-8").read()
        return [int(x) for x in re.findall(r"\d+", txt) if 0 <= int(x) <= 36]
    # padrão: banco do bot
    import sqlite3
    from config.settings import Settings
    conn = sqlite3.connect(str(Settings.DB_PATH))
    cur = conn.cursor()
    cur.execute("SELECT number FROM numbers ORDER BY detected_at ASC")
    nums = [r[0] for r in cur.fetchall()]
    conn.close()
    return [n for n in nums if isinstance(n, int) and 0 <= n <= 36]


def top_set(seq, n=TOP):
    return set(num for num, _ in Counter(seq).most_common(n))


def chunks(seq, k):
    L = len(seq) // k
    return [seq[i * L:(i + 1) * L] for i in range(k)]


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    nums = carregar(arg)
    n = len(nums)
    print(f"Histórico: {n} números\n")
    if n < 400:
        print("Poucos dados para conclusão confiável (ideal 2000+).")
        return

    # 1) Top-16 da 1ª metade vs 2ª metade
    h1, h2 = nums[: n // 2], nums[n // 2:]
    t1, t2 = top_set(h1), top_set(h2)
    overlap = len(t1 & t2)
    print("1) TOP-16 mais quentes: 1ª metade vs 2ª metade")
    print(f"   1ª metade: {sorted(t1)}")
    print(f"   2ª metade: {sorted(t2)}")
    print(f"   coincidem: {overlap}/16   (acaso ~ {TOP*TOP/37:.1f})")
    print(f"   -> {'PERSISTÊNCIA (viés?)' if overlap >= 12 else 'EMBARALHA (variância) — sem conjunto fixo'}\n")

    # 2) Números top-16 em TODOS os 4 quartos
    tops = [top_set(q) for q in chunks(nums, 4)]
    sempre = set.intersection(*tops)
    chance_sempre = (16 / 37) ** 4 * 37
    print("2) Números no TOP-16 em TODOS os 4 quartos do histórico")
    print(f"   'sempre quente': {sorted(sempre)}  ({len(sempre)} nºs · acaso ~{chance_sempre:.1f})")
    print(f"   -> {'CONJUNTO FIXO REAL!' if len(sempre) >= 10 else 'consistente com o ACASO — não há 16 fixos'}\n")

    # 3) Mais quentes e mais frios no total
    cnt = Counter(nums)
    esp = n / 37
    desvios = sorted(((cnt.get(k, 0) - esp) / esp * 100, k) for k in range(37))
    print("3) Os 5 mais QUENTES e mais FRIOS (desvio % da média)")
    for d, k in desvios[-5:][::-1]:
        print(f"   nº {k:>2}: {cnt.get(k,0):>3}x  ({d:+.0f}%)")
    print("   ...")
    for d, k in desvios[:5]:
        print(f"   nº {k:>2}: {cnt.get(k,0):>3}x  ({d:+.0f}%)")


if __name__ == "__main__":
    main()
