from collections import Counter
from typing import List, Optional
import logging

logger = logging.getLogger('market_analysis')

# Definição física das zonas da roleta
ZONES = {
    "VIZINHOS": [22, 18, 29, 7, 28, 12, 35, 3, 26, 0, 32, 15, 19, 4, 21, 2, 25],
    "TIER": [27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33],
    "ORPHELINS": [1, 20, 14, 31, 9, 17, 34, 6]
}

REDS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]

SUSPICIOUS_NUMBERS = [2, 4, 8, 13, 15, 20, 30]

def get_zone(num: int) -> str:
    for zone_name, numbers in ZONES.items():
        if num in numbers:
            return zone_name
    return "UNKNOWN"

def get_properties(n: int) -> List[str]:
    """Retorna lista de atributos (cor, paridade, altura, dúzia, coluna)."""
    if n == 0:
        return ["ZERO"]
    
    props = []
    # Cor
    props.append("RED" if n in REDS else "BLACK")
    # Paridade
    props.append("EVEN" if n % 2 == 0 else "ODD")
    # Altura
    props.append("LOW" if 1 <= n <= 18 else "HIGH")
    # Dúzia
    if 1 <= n <= 12: props.append("DOZEN1")
    elif 13 <= n <= 24: props.append("DOZEN2")
    else: props.append("DOZEN3")
    # Coluna
    if n % 3 == 1: props.append("COLUMN1")
    elif n % 3 == 2: props.append("COLUMN2")
    else: props.append("COLUMN3")
    
    return props

def check_streaks(recent_numbers: List[int], threshold: int = 5) -> Optional[str]:
    """Verifica se há repetições excessivas (monotonia/turbulência de sequência)."""
    if len(recent_numbers) < threshold:
        return None

    history = recent_numbers[-threshold:]
    
    # Mapeia propriedades para cada número no histórico
    prop_history = [get_properties(n) for n in history]
    
    # Pega as propriedades do primeiro número (o mais antigo da fatia threshold)
    # e verifica se elas se mantêm em todos os números subsequentes da fatia
    candidate_props = prop_history[0]
    
    # Se o primeiro número for ZERO, ele só tem ["ZERO"]. Se o streak for de ZEROs, ok.
    # Mas se misturar ZERO com cores, o get_properties(0) retorna só ["ZERO"].
    # A lógica abaixo assume que queremos ver se uma propriedade se repete.
    # Se aparecer um ZERO no meio de uma sequência de REDs, tecnicamente quebra a sequência de REDs?
    # Na roleta, sim, zero não é vermelho nem preto. Então quebra.
    
    for prop in candidate_props:
        if prop == "ZERO": 
            # Se for streak de zeros, também é turbulência? Provavelmente sim.
            pass
            
        # Verifica se 'prop' está presente em todos os itens do histórico recente
        is_streak = all(prop in p_list for p_list in prop_history)
        if is_streak:
            return prop
            
    return None

def check_suspicious_repetition(recent_numbers: List[int]) -> bool:
    """
    Verifica a frequência de números suspeitos nos últimos 20 giros.
    Retorna True se estiver SEGURO (frequência <= 40%).
    Retorna False se estiver TURBULENTO (frequência > 40%).
    """
    if not recent_numbers:
        return True
        
    last_20 = recent_numbers[-20:]
    total = len(last_20)
    if total == 0:
        return True
        
    count = sum(1 for n in last_20 if n in SUSPICIOUS_NUMBERS)
    ratio = count / total
    
    if ratio > 0.40:
        logger.info(f"🚫 TURBULÊNCIA: Números suspeitos {count}/{total} ({ratio:.1%}) > 40%")
        return False
        
    return True

def analyze_market(recent_numbers: List[int], lookback: int = 8) -> dict:
    """
    Análise de Inteligência de Mercado.
    Retorna dicionário com status e motivo.
    """
    res = {"secure": True, "reason": None, "type": None}
    
    if len(recent_numbers) < 5:
        return res
        
    # 1. Check Streaks (Sequência Excessiva 4+)
    # Conforme pedido: "sempre que cair 4 vezes automaticamente ele ja iria mandar a mensagem"
    streak_prop = check_streaks(recent_numbers, threshold=4)
    if streak_prop:
        res.update({
            "secure": False, 
            "type": "MANIPULACAO",
            "reason": f"Sequência excessiva ({streak_prop}) identificada!"
        })
        return res

    # 2. Check Suspicious Numbers (> 40% nos últimos 20)
    if not check_suspicious_repetition(recent_numbers):
        res.update({
            "secure": False, 
            "type": "TURBULENCIA",
            "reason": "Alta frequência de números viciados detectada."
        })
        return res

    # 3. Análise de Fluidez / "Embaraçada"
    slice_size = min(len(recent_numbers), lookback)
    history_slice = recent_numbers[-slice_size:]
    
    terminals = [n % 10 for n in history_slice]
    term_counts = Counter(terminals)
    max_term_rep = max(term_counts.values()) if term_counts else 0
    
    zones = [get_zone(n) for n in history_slice]
    zone_counts = Counter(zones)
    if "UNKNOWN" in zone_counts:
        del zone_counts["UNKNOWN"]
    max_zone_rep = max(zone_counts.values()) if zone_counts else 0
    
    is_terminal_fluid = max_term_rep >= 2
    is_zone_fluid = max_zone_rep >= 3 
    
    # "Embaraçada" = Todos os terminais são diferentes nos últimos 5-6 giros
    if len(history_slice) >= 6 and max_term_rep == 1:
        res.update({
            "secure": False, 
            "type": "TURBULENCIA",
            "reason": "Timeline instável (Terminais desconexos)."
        })
        return res

    if not (is_terminal_fluid or is_zone_fluid):
        res.update({
            "secure": False, 
            "type": "TURBULENCIA",
            "reason": "Mercado lateralizado/sem padrão definido."
        })
        return res
        
    return res
