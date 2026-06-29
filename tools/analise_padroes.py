"""
analise_padroes.py — Análise estatística RIGOROSA do histórico de roleta.

Procura padrões REAIS (viés de roda) e testa as crenças comuns (repetição,
"região depois do número", sequências) contra o acaso. Lê do BANCO do bot.

Uso:
  python tools/analise_padroes.py            # usa o banco do bot
  python tools/analise_padroes.py nums.txt   # usa um arquivo de números
"""
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.getcwd())

# Layout da roda europeia (ordem física = "Pista/Race")
WHEEL = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5,
         24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26]
POS = {n: i for i, n in enumerate(WHEEL)}


def carregar(arg=None):
    if arg:
        txt = open(arg, encoding="utf-8").read()
        return [int(x) for x in re.findall(r"\d+", txt) if 0 <= int(x) <= 36]
    import sqlite3
    from config.settings import Settings
    conn = sqlite3.connect(str(Settings.DB_PATH))
    cur = conn.cursor()
    cur.execute("SELECT number FROM numbers ORDER BY detected_at ASC")
    nums = [r[0] for r in cur.fetchall()]
    conn.close()
    return [n for n in nums if isinstance(n, int) and 0 <= n <= 36]


def wheel_dist(a, b):
    d = abs(POS[a] - POS[b])
    return min(d, 37 - d)


def analisar(nums):
    n = len(nums)
    print(f"=== {n} números ===\n")

    # 1) Qui-quadrado (viés)
    exp = n / 37.0
    cnt = Counter(nums)
    chi = sum((cnt.get(k, 0) - exp) ** 2 / exp for k in range(37))
    print("1) TESTE DE VIÉS (qui-quadrado, df=36)")
    print(f"   chi² = {chi:.1f}  (crítico 95%=51.0 · 99%=58.6)")
    print(f"   -> {'VIÉS!' if chi > 58.6 else 'sugestivo (95%)' if chi > 51 else 'roda JUSTA'}")
    if n < 1500:
        print("   ⚠️ amostra pequena — ideal 2000+")
    print()

    # 2) Quentes / frios
    print("2) QUENTES / FRIOS")
    print(f"   quentes: {[(k, c) for k, c in cnt.most_common(5)]}")
    print(f"   frios:   {[(k, cnt.get(k,0)) for k in sorted(range(37), key=lambda k: cnt.get(k,0))[:5]]}")
    print()

    # 3) Repetição imediata
    rep = sum(1 for i in range(1, n) if nums[i] == nums[i - 1])
    print("3) REPETIÇÃO IMEDIATA (X depois de X)")
    print(f"   observado {rep} | esperado {(n-1)/37:.1f} -> {'acima' if rep > (n-1)/37*1.5 else 'dentro do acaso'}")
    print()

    # 4) Região depois (distância na pista)
    dists = [wheel_dist(nums[i - 1], nums[i]) for i in range(1, n)]
    perto = sum(1 for d in dists if d <= 3)
    print("4) REGIÃO DEPOIS (distância na pista entre giros)")
    print(f"   média {sum(dists)/len(dists):.1f} (acaso ~9.5) | perto(<=3) {100*perto/len(dists):.0f}% (acaso ~19%)")
    print(f"   -> {'agrupamento setorial?' if perto/len(dists) > 0.27 else 'próximo número independente'}")
    print()

    # 5) Sequências
    def maior_seq(fn):
        cur = best = 0; prev = None
        for x in nums:
            if x == 0:
                prev = None; cur = 0; continue
            v = fn(x)
            cur = cur + 1 if v == prev else 1
            prev = v; best = max(best, cur)
        return best
    print("5) SEQUÊNCIAS (mudança de padrão)")
    print(f"   maior par/ímpar: {maior_seq(lambda x: x % 2)} | baixo/alto: {maior_seq(lambda x: x <= 18)}")
    print(f"   (4-5 seguidas é comum: acaso ~{(18/37)**4*100:.0f}%)")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    nums = carregar(arg)
    if len(nums) < 50:
        print("Poucos números no histórico.")
    else:
        analisar(nums)
