import math
from typing import List, Dict, Tuple

class StatisticalEngine:
    """
    Motor de análise estatística para roleta (Janela de 60 giros).
    Calcula desvios baseados em frequência esperada (Mu) e desvio padrão (Sigma).
    """

    @staticmethod
    def calc_mu_sigma(n: int, p: float) -> Tuple[float, float]:
        """
        Calcula média (mu) e desvio padrão (sigma) para distribuição binomial.
        n: tamanho da amostra (giros)
        p: probabilidade do evento (ex: 1/37 para um número)
        """
        mu = n * p
        sigma = math.sqrt(n * p * (1 - p))
        return mu, sigma

    def analyze_window(self, history: List[int]) -> Dict:
        """
        Analisa os últimos N giros e retorna os desvios por categoria.
        """
        n = len(history)
        if n == 0:
            return {}

        results = {
            "numeros": {},
            "cores": {"RED": 0, "BLACK": 0},
            "duzias": {"D1": 0, "D2": 0, "D3": 0},
            "colunas": {"C1": 0, "C2": 0, "C3": 0},
            "paridade": {"EVEN": 0, "ODD": 0},
            "altura": {"HIGH": 0, "LOW": 0}
        }

        # Definições de Grupos
        REDS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
        
        for num in history:
            # Números Individuais
            results["numeros"][num] = results["numeros"].get(num, 0) + 1
            
            if num == 0:
                continue

            # Cores
            if num in REDS: results["cores"]["RED"] += 1
            else: results["cores"]["BLACK"] += 1

            # Dúzias
            if 1 <= num <= 12: results["duzias"]["D1"] += 1
            elif 13 <= num <= 24: results["duzias"]["D2"] += 1
            else: results["duzias"]["D3"] += 1

            # Colunas
            col = num % 3
            if col == 1: results["colunas"]["C1"] += 1
            elif col == 2: results["colunas"]["C2"] += 1
            else: results["colunas"]["C3"] += 1

            # Paridade
            if num % 2 == 0: results["paridade"]["EVEN"] += 1
            else: results["paridade"]["ODD"] += 1

            # Altura
            if 19 <= num <= 36: results["altura"]["HIGH"] += 1
            else: results["altura"]["LOW"] += 1

        # Cálculo de Desvios (Z-Score aproximado: (Obs - Mu) / Sigma)
        outliers = []
        summary = {}

        # 1. Números (p = 1/37)
        mu, sigma = self.calc_mu_sigma(n, 1/37)
        for num, freq in results["numeros"].items():
            z = (freq - mu) / sigma if sigma > 0 else 0
            if z > 1: # Rastreia qualquer coisa acima de 1 sigma
                summary[f"Num_{num}"] = z

        # 2. Cores, Paridade, Altura (p = 18/37)
        mu_dual, sigma_dual = self.calc_mu_sigma(n, 18/37)
        for cat in ["cores", "paridade", "altura"]:
            for key, freq in results[cat].items():
                z = (freq - mu_dual) / sigma_dual if sigma_dual > 0 else 0
                summary[f"{cat}_{key}"] = z

        # 3. Dúzias, Colunas (p = 12/37)
        mu_tri, sigma_tri = self.calc_mu_sigma(n, 12/37)
        for cat in ["duzias", "colunas"]:
            for key, freq in results[cat].items():
                z = (freq - mu_tri) / sigma_tri if sigma_tri > 0 else 0
                summary[f"{cat}_{key}"] = z

        return summary

# Instância Global
engine = StatisticalEngine()
