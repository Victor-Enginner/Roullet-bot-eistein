"""
vies_hunter.py — Caça-viés da Roleta Brasileira (comando /vies do Telegram).

Roda em TODO o histórico acumulado no banco do bot:
  - qui-quadrado de uniformidade (a roda é justa ou tem viés real?)
  - persistência dos quentes (os 16 mais quentes se mantêm entre períodos?)

Conclusão honesta: provavelmente vai dar "justa" por muito tempo (roleta online
regulada é mantida pra não ter viés). Mas conforme o histórico cresce, o teste
fica forte o bastante pra ACHAR ou DESCARTAR de vez qualquer viés mínimo.
"""
import sqlite3
from collections import Counter

from config.settings import Settings


def _carregar_numeros(db_path: str):
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT number FROM numbers ORDER BY detected_at ASC")
        nums = [r[0] for r in cur.fetchall()]
        conn.close()
        return [n for n in nums if isinstance(n, int) and 0 <= n <= 36]
    except Exception:
        return []


def analisar_vies(db_path: str = None) -> str:
    """Devolve um resumo do caça-viés pronto para enviar ao Telegram."""
    db_path = db_path or str(Settings.DB_PATH)
    nums = _carregar_numeros(db_path)
    n = len(nums)

    if n < 500:
        return (
            "🔬 CAÇA-VIÉS\n"
            f"Poucos dados ({n} números). Preciso de pelo menos 500 "
            "(ideal 2000+) para um teste confiável. Continue jogando que o "
            "histórico cresce sozinho."
        )

    # --- Qui-quadrado de uniformidade ---
    exp = n / 37.0
    cnt = Counter(nums)
    chi = sum((cnt.get(k, 0) - exp) ** 2 / exp for k in range(37))
    if chi > 58.6:
        veredito = "⚠️ VIÉS FORTE (99%)"
    elif chi > 51.0:
        veredito = "⚠️ viés sugestivo (95%)"
    else:
        veredito = "✅ justa (sem viés detectável)"

    # --- Persistência dos top-16 (1ª metade vs 2ª metade) ---
    meio = n // 2
    t1 = set(x for x, _ in Counter(nums[:meio]).most_common(16))
    t2 = set(x for x, _ in Counter(nums[meio:]).most_common(16))
    overlap = len(t1 & t2)
    persist = "PERSISTEM (possível viés!)" if overlap >= 12 else "embaralham (variância — sem fixos)"

    quentes = ", ".join(f"{k}({c}x)" for k, c in cnt.most_common(5))
    frios = ", ".join(f"{k}({cnt.get(k,0)}x)" for k in
                      sorted(range(37), key=lambda k: cnt.get(k, 0))[:5])

    edge = chi > 51.0 and overlap >= 12
    rodape = (
        "🎯 EDGE POSSÍVEL — mande /vies de novo mais tarde pra confirmar se persiste!"
        if edge else
        "Segue justa. Continue acumulando — quanto mais giros, mais forte o teste."
    )

    return (
        "🔬 CAÇA-VIÉS — Roleta Brasileira\n"
        f"📊 {n} números acumulados\n\n"
        f"Qui-quadrado: {chi:.0f}  (crítico 95%=51 · 99%=58.6)\n"
        f"→ {veredito}\n\n"
        f"Top-16 quentes (1ª vs 2ª metade): {overlap}/16 coincidem (acaso ~7)\n"
        f"→ {persist}\n\n"
        f"🔥 Quentes: {quentes}\n"
        f"❄️ Frios: {frios}\n\n"
        f"{rodape}"
    )
