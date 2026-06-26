import logging
from typing import List, Tuple, Dict
from config.settings import Settings
from utils.rule_engine import engine

logger = logging.getLogger('context_filter')

class ContextFilter:
    """
    Filtro de Contexto Baseado em Estatística (Mu + Sigma).
    Implementa a regra de janela mínima de 60 giros e detecção de turbulência extrema.
    """

    def should_block_entry(self, history: List[int], current_number: int) -> Tuple[bool, Dict]:
        """
        Analisa a mesa para detectar turbulência.
        No modelo 'Alert-Only', isso não bloqueia, apenas gera o alerta de risco.
        """
        n = len(history)
        # 1. Janela Mínima de Sequência (4 giros)
        if n < 4:
            return False, {"type": "initializing", "stats": {}}

        # 2. Detecção de Sequências (4-in-a-row) - RECOMENDAÇÃO DO USUÁRIO
        # Categorias de Verificação
        REDS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
        D1, D2, D3 = range(1, 13), range(13, 25), range(25, 37)
        C1 = [x for x in range(1, 37) if x % 3 == 1]
        C2 = [x for x in range(1, 37) if x % 3 == 2]
        C3 = [x for x in range(1, 37) if x % 3 == 0]
        
        last_4 = history[-4:]
        sequences_hit = []
        
        # Verificações de 4 seguidos
        if len(last_4) == 4:
            if all(x in REDS for x in last_4): sequences_hit.append("4 VERMELHOS")
            elif all(x > 0 and x not in REDS for x in last_4): sequences_hit.append("4 PRETOS")
            
            if all(x > 0 and x % 2 == 0 for x in last_4): sequences_hit.append("4 PARES")
            elif all(x % 2 != 0 for x in last_4): sequences_hit.append("4 ÍMPARES")
            
            if all(x >= 19 for x in last_4): sequences_hit.append("4 ALTOS")
            elif all(1 <= x <= 18 for x in last_4): sequences_hit.append("4 BAIXOS")
            
            if all(x in D1 for x in last_4): sequences_hit.append("4 DÚZIA 1")
            elif all(x in D2 for x in last_4): sequences_hit.append("4 DÚZIA 2")
            elif all(x in D3 for x in last_4): sequences_hit.append("4 DÚZIA 3")
            
            if all(x in C1 for x in last_4): sequences_hit.append("4 COLUNA 1")
            elif all(x in C2 for x in last_4): sequences_hit.append("4 COLUNA 2")
            elif all(x in C3 for x in last_4): sequences_hit.append("4 COLUNA 3")

        # 3. Janela Mínima de Estatística (60 giros) - Somente Mu+Sigma
        if n < Settings.STATS_WINDOW_SIZE:
            has_turbulence = len(sequences_hit) > 0
            return has_turbulence, {
                "type": "warming_up" if not has_turbulence else "moderate_turbulence",
                "label": "AQUECIMENTO" if not has_turbulence else "SEQUÊNCIA DETECTADA",
                "current_size": n,
                "categories": sequences_hit,
                "stats": {}
            }

        # 3. Análise Estatística (Janela 60)
        history_window = history[-Settings.STATS_WINDOW_SIZE:]
        stats_summary = engine.analyze_window(history_window)
        
        # Detecção de Outliers EXTREMOS (> 3.0 Sigma)
        extreme_outliers = {k: v for k, v in stats_summary.items() if v > Settings.TURBULENCE_TH_SIGMA}
        
        # 4. Consolidação da Turbulência
        categories_hit = set(sequences_hit)
        for key, z in extreme_outliers.items():
            if "cores_" in key: categories_hit.add("DESVIO COR")
            elif "duzias_" in key: categories_hit.add("DESVIO DUZIA")
            elif "colunas_" in key: categories_hit.add("DESVIO COLUNA")
            elif "paridade_" in key: categories_hit.add("DESVIO PARIDADE")
            elif "altura_" in key: categories_hit.add("DESVIO ALTURA")

        has_turbulence = len(categories_hit) > 0
        
        if has_turbulence:
            logger.info(f"🌪️ Turbulência Detectada: {list(categories_hit)}")
            return True, {
                "type": "extreme_turbulence" if len(categories_hit) >= 2 else "moderate_turbulence",
                "label": "TURBULÊNCIA DETECTADA",
                "categories": list(categories_hit),
                "stats": stats_summary
            }

        return False, {"stats": stats_summary}
