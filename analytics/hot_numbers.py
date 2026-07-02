"""
hot_numbers.py — Números quentes com base em dados REAIS do banco (comando /quentes).

Diferente do /vies (que usa TODO o histórico acumulado), esta análise olha
apenas para uma JANELA recente de giros (últimos N números salvos), o que é
mais útil para detectar tendências de curto prazo do que o histórico inteiro.

Também é independente do buffer em memória usado hoje pelo Ollama: lê sempre
direto de data/database.sqlite (tabela `numbers`, coluna `number`,
ordenada por `detected_at`).
"""
import sqlite3
from collections import Counter
from typing import List, Optional, Tuple

from config.settings import Settings


def _carregar_ultimos_numeros(db_path: str, window: int) -> List[int]:
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT number FROM numbers ORDER BY detected_at DESC LIMIT ?",
            (window,),
        )
        nums = [r[0] for r in cur.fetchall()]
        conn.close()
        return [n for n in nums if isinstance(n, int) and 0 <= n <= 36]
    except Exception:
        return []


def get_hot_numbers(
    db_path: Optional[str] = None,
    window: int = 100,
    top_n: int = 8,
) -> Tuple[List[Tuple[int, int]], int]:
    """
    Lê os últimos `window` números REAIS salvos em data/database.sqlite
    (ORDER BY detected_at DESC LIMIT window), conta a frequência de cada
    número na amostra e devolve os `top_n` mais frequentes.

    Retorna uma tupla (top, sample_size):
      - top: lista de (numero, contagem) ordenada da maior para a menor
        frequência, no máximo `top_n` itens.
      - sample_size: quantidade real de números usados na amostra (pode
        ser menor que `window` se o banco ainda não tiver `window`
        registros).
    """
    db_path = db_path or str(Settings.DB_PATH)
    nums = _carregar_ultimos_numeros(db_path, window)
    sample_size = len(nums)

    if sample_size == 0:
        return [], 0

    contagem = Counter(nums)
    top = contagem.most_common(top_n)
    return top, sample_size
