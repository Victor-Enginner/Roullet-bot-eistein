"""
backtest_principal.py — Backtest das estratégias REAIS do principal.

Replica a decisão do bot (pick_strategy + máquina de estados: entrada + até 3
proteções) sobre todo o histórico de números e compara com o resultado REAL
gravado na tabela `results`.

Objetivo honesto: mostrar que a taxa de ~99% vem da COBERTURA + martingale
(cobre ~27 números e tem 4 chances), não de um edge. E que as raras perdas são
as caras (gale escalando), então a taxa alta é o perfil clássico do martingale.

Uso: python tools/backtest_principal.py
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.getcwd())

from config.settings import Settings
from server.agents.strategy import pick_strategy
from engine.parser import parse_strategy_targets, parse_protection_targets

MAX_PROT = 3  # principal: entrada + 3 proteções


def carregar_numeros():
    conn = sqlite3.connect(str(Settings.DB_PATH))
    cur = conn.cursor()
    cur.execute("SELECT number FROM numbers ORDER BY detected_at ASC")
    nums = [r[0] for r in cur.fetchall()]
    conn.close()
    return [n for n in nums if isinstance(n, int) and 0 <= n <= 36]


CHIP = 0.50  # ficha por número (BetCreator)


def simular(nums, i, entry, prot):
    """Entrada no índice i; resolve em até MAX_PROT+1 giros."""
    for j in range(1, MAX_PROT + 2):  # 1 (entrada) .. MAX_PROT+1
        if i + j >= len(nums):
            return None
        r = nums[i + j]
        if r in entry:
            return "WIN_ENTRY"
        if r == 0 or r in prot:
            return "WIN_PROTECTION"
    return "LOSS"


def simular_pnl(nums, i, entry, prot):
    """P&L em R$ da sequência, ficha 0.50/número, gale FLAT (re-aposta igual).
    Rodada 1 = entrada; rodadas 2..4 = proteção. Vence se o número está na
    aposta da rodada (ou 0, coberto à parte). Retorna (pnl, None) se faltar giro.
    """
    pnl = 0.0
    rodadas = [entry] + [prot] * MAX_PROT
    for j, aposta in enumerate(rodadas):
        if i + 1 + j >= len(nums):
            return None
        K = len(aposta)
        r = nums[i + 1 + j]
        if r in aposta:   # só ganha se o nº apostado bater (zero é cobertura à parte)
            pnl += CHIP * 36 - CHIP * K
            return pnl
        pnl -= CHIP * K  # errou esta rodada
    return pnl  # perdeu todas


def real_results():
    try:
        conn = sqlite3.connect(str(Settings.DB_PATH))
        cur = conn.cursor()
        cur.execute("SELECT event_type, COUNT(*) FROM results GROUP BY event_type")
        d = dict(cur.fetchall())
        conn.close()
        return d
    except Exception:
        return {}


def main():
    nums = carregar_numeros()
    forb = set(getattr(Settings, "FORBIDDEN_NUMBERS", []))
    we = wp = loss = 0
    soma_K = 0
    pnl_total = 0.0
    for i in range(len(nums) - (MAX_PROT + 1)):
        base = nums[i]
        if base in forb:
            continue
        s = pick_strategy(base, nums[: i + 1])
        entrada = s.get("entrada")
        if not entrada:
            continue
        entry = set(parse_strategy_targets(entrada))
        if not entry:
            continue
        prot = set(parse_protection_targets(s.get("cobertura", "")))
        res = simular(nums, i, entry, prot)
        if res is None:
            continue
        soma_K += len(entry | prot)
        p = simular_pnl(nums, i, entry, prot)
        if p is not None:
            pnl_total += p
        if res == "WIN_ENTRY":
            we += 1
        elif res == "WIN_PROTECTION":
            wp += 1
        else:
            loss += 1

    total = we + wp + loss
    if not total:
        print("Sem entradas simuladas (histórico insuficiente).")
        return
    taxa = (we + wp) / total
    K = soma_K / total
    chance = 1 - ((37 - K) / 37) ** (MAX_PROT + 1)  # cobrir K em 4 giros

    print(f"=== BACKTEST do PRINCIPAL ({total} entradas simuladas) ===")
    print(f"  WIN_ENTRY: {we}  | WIN_PROTECTION: {wp}  | LOSS: {loss}")
    print(f"  TAXA DE ACERTO: {taxa*100:.1f}%")
    print(f"  cobertura média ~{K:.0f} números, 4 chances -> acaso = {chance*100:.1f}%")
    print()
    pnl_por_entrada = pnl_total / total
    print(f"  💰 P&L (ficha 0.50/nº, gale flat): R$ {pnl_total:+.2f} em {total} entradas")
    print(f"     = R$ {pnl_por_entrada:+.2f} por entrada")
    print(f"     projetado nas suas 763 entradas reais: R$ {pnl_por_entrada*763:+.0f}")
    print()
    real = real_results()
    if real:
        rt = real.get("WIN_ENTRY", 0) + real.get("WIN_PROTECTION", 0)
        rl = real.get("LOSS", 0)
        rtotal = rt + rl
        print(f"=== RESULTADO REAL gravado ({rtotal} entradas ao vivo) ===")
        print(f"  greens: {rt}  | losses: {rl}  -> {rt/rtotal*100:.1f}% de acerto")
        print()
    print("LEITURA HONESTA:")
    print(f"  A taxa alta ({taxa*100:.0f}%) = COBERTURA. Cobrindo ~{K:.0f} de 37 números")
    print(f"  com 4 chances (entrada + 3 gales), acertar ~{chance*100:.0f}% é o ACASO,")
    print("  não edge. As raras perdas são as CARAS (gale escalando) -> perfil")
    print("  clássico do martingale: ganha quase sempre pouco, perde raro e muito.")


if __name__ == "__main__":
    main()
