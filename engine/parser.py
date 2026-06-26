import re
from typing import List, Set
from .calculator import get_neighbors, get_terminal_numbers

def parse_strategy_targets(input_str: str) -> List[int]:
    """
    Analisa a string de entrada e retorna lista de números alvo.
    Suporta:
    - "T1 e T3 com 1 vizinho"
    - "T5 com 2 vizinhos"
    - "9 / 19 / 29 com 2 vizinhos"
    - "27 e 7 com 5 vizinhos"
    - "11 / 22 / 33 / 0 com 3 vizinhos"
    - "Tier" (Região Tier)
    """
    text = input_str.lower().strip()
    targets = set()
    
    # 1. Tratamento específico para "X vizinhos do número Y" (Legado/Estratégia 0)
    match_legacy = re.search(r'(\d+)\s+vizinhos\s+do\s+número\s+(\d+)', text)
    if match_legacy:
        count = int(match_legacy.group(1))
        center = int(match_legacy.group(2))
        targets.update(get_neighbors(center, count))
        # Se tiver mais coisas, o parser abaixo tenta pegar. Mas geralmente é só isso.
    
    # 2. Identifica "Tier"
    # Se "tier" mencinado, adiciona números do Tier
    # Se for "Tier com X vizinhos", será tratado no loop abaixo
    if "tier" in text and "com" not in text:
         from .calculator import TIER_NUMBERS
         targets.update(TIER_NUMBERS)

    # 3. Padrão principal "Alvos com X vizinhos"
    # Grupo 1: Lista de alvos (T1, 9, 19, Tier, etc)
    # Grupo 2: Quantidade de vizinhos
    vizinhos_match = re.search(r'(.+?)\s+com\s+(\d+)\s+vizinhos?', text)
    
    if vizinhos_match:
        raw_targets = vizinhos_match.group(1)
        neighbors_count = int(vizinhos_match.group(2))
        
        # Separa os alvos por '/', 'e', ','
        target_tokens = re.split(r'\s*[\/e,]\s*', raw_targets)
        
        for token in target_tokens:
            token = token.strip()
            if not token:
                continue
            
            # Suporte a "Tier" com vizinhos
            if "tier" in token:
                 from .calculator import TIER_NUMBERS
                 for num in TIER_NUMBERS:
                     targets.update(get_neighbors(num, neighbors_count))
                 continue

            # Verifica se é Terminal (T1, T2...)
            t_match = re.match(r'^t(\d)$', token)
            if t_match:
                terminal = int(t_match.group(1))
                terminal_nums = get_terminal_numbers(terminal)
                for num in terminal_nums:
                    targets.update(get_neighbors(num, neighbors_count))
            # Verifica se é um número direto (9, 19, 0...)
            elif token.isdigit():
                num = int(token)
                targets.update(get_neighbors(num, neighbors_count))

    return sorted(list(targets))

def parse_protection_targets(input_str: str) -> List[int]:
    """
    Analisa alvos de proteção.
    Suporta Terminais (T4) ou números diretos (33, 5).
    Ex: "T4 / T7" ou "33, 5, 10"
    """
    text = input_str.upper()
    targets = set()

    # Extrai Terminais T0-T9
    terminals = re.findall(r'T(\d+)', text)
    for t in terminals:
        term_nums = get_terminal_numbers(int(t))
        targets.update(term_nums)

    # Limpa T-patterns para extrair números isolados
    clean_text = re.sub(r'T\d+', '', text)
    
    # Extrai números restantes
    nums = re.findall(r'\b(\d+)\b', clean_text)
    for n in nums:
        targets.add(int(n))

    return sorted(list(targets))
