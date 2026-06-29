import math
import json
import os
import logging
import threading
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger("ai.smart_brain")

# Layout oficial do cilindro da roleta europeia (single zero)
WHEEL_LAYOUT = [
    0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5,
    24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26
]

WHEEL_POSITIONS = {num: pos for pos, num in enumerate(WHEEL_LAYOUT)}


class CroupierSignatureTracker:
    """
    Rastreia e analisa a assinatura física (geométrica) do crupiê.
    Mede a distância angular em casas percorrida pela bola no cilindro
    e detecta se os lançamentos estão com força/distância constantes.
    """
    def __init__(self, sample_size: int = 15, max_std_dev: float = 4.0):
        self.sample_size = sample_size
        self.max_std_dev = max_std_dev
        self.history: List[int] = []

    def add_spin(self, number: int):
        if number in WHEEL_POSITIONS:
            self.history.append(number)
            if len(self.history) > self.sample_size:
                self.history.pop(0)

    def calculate_distances(self) -> List[int]:
        """Calcula a distância circular em casas entre giros consecutivos."""
        if len(self.history) < 2:
            return []
        
        distances = []
        for i in range(1, len(self.history)):
            pos_prev = WHEEL_POSITIONS[self.history[i-1]]
            pos_curr = WHEEL_POSITIONS[self.history[i]]
            # Distância circular horária (0 a 36)
            dist = (pos_curr - pos_prev) % 37
            distances.append(dist)
        return distances

    def get_croupier_signature(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Retorna a distância média circular e o desvio padrão circular
        dos lançamentos do crupiê na amostra recente.
        """
        distances = self.calculate_distances()
        if not distances or len(distances) < 8:
            return None, None

        # Para cálculo circular robusto, convertemos distâncias para ângulos
        angles = [d * (2 * math.pi / 37) for d in distances]
        
        # Média dos componentes vetoriais
        sum_sin = sum(math.sin(a) for a in angles)
        sum_cos = sum(math.cos(a) for a in angles)
        avg_sin = sum_sin / len(angles)
        avg_cos = sum_cos / len(angles)
        
        # Ângulo médio
        avg_angle = math.atan2(avg_sin, avg_cos) % (2 * math.pi)
        mean_dist = (avg_angle * 37 / (2 * math.pi)) % 37
        
        # Desvio padrão circular aproximado
        r = math.sqrt(avg_sin**2 + avg_cos**2)
        std_dev = math.sqrt(-2.0 * math.log(r)) * 37 / (2 * math.pi) if r > 0.001 else 37.0
        
        return mean_dist, std_dev

    def predict_target_sector(self, last_number: int, radius: int = 2) -> List[int]:
        """
        Se o crupiê tiver uma assinatura consistente (baixo desvio padrão),
        prevê os números do setor provável para a próxima queda.
        """
        if last_number not in WHEEL_POSITIONS:
            return []

        mean_dist, std_dev = self.get_croupier_signature()
        if mean_dist is None or std_dev is None:
            return []

        # Se o desvio padrão for menor que o limite, há consistência física
        if std_dev <= self.max_std_dev:
            pos_last = WHEEL_POSITIONS[last_number]
            # Projeta a posição média futura
            predicted_pos = int(round(pos_last + mean_dist)) % 37
            
            # Pega o setor de vizinhos ao redor da posição prevista
            sector_positions = [
                (predicted_pos + offset) % 37
                for offset in range(-radius, radius + 1)
            ]
            predicted_numbers = [WHEEL_LAYOUT[pos] for pos in sector_positions]
            logger.info(
                f"🎯 [SmartBrain] Assinatura detectada! Desvio padrão circular: {std_dev:.2f}. "
                f"Setor previsto ao redor do número {WHEEL_LAYOUT[predicted_pos]}: {predicted_numbers}"
            )
            return predicted_numbers
        
        return []


class MesaQLearning:
    """
    Aprendizado por reforço simples para auto-calibrar pesos das estratégias
    durante a sessão baseado na assertividade real.
    """
    def __init__(self, file_path: str = "data/q_learning_weights.json"):
        self.file_path = file_path
        self.weights: Dict[str, float] = {}
        self.load_weights()

    def load_weights(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.weights = json.load(f)
            except Exception as e:
                logger.warning(f"Erro ao carregar pesos Q-Learning: {e}")
                self.weights = {}

    def save_weights(self):
        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.weights, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Erro ao salvar pesos Q-Learning: {e}")

    def get_weight(self, strategy_id: int) -> float:
        # Peso padrão é 1.0, limites de 0.5 a 1.5
        return self.weights.get(str(strategy_id), 1.0)

    def register_outcome(self, strategy_id: int, outcome: str):
        """
        Ajusta os pesos de recompensa baseados em acertos e erros.
        outcome: 'green' | 'g1' | 'loss'
        """
        sid = str(strategy_id)
        current = self.weights.get(sid, 1.0)
        
        if outcome in ("green", "g1"):
            # Aumenta peso por assertividade recente
            reward = 0.05
            self.weights[sid] = min(1.5, current + reward)
            logger.info(f"📈 [SmartBrain] Recompensa Q-Learning para Estratégia #{strategy_id}: {current:.2f} -> {self.weights[sid]:.2f}")
        elif outcome == "loss":
            # Reduz peso agressivamente por erro
            penalty = 0.15
            self.weights[sid] = max(0.5, current - penalty)
            logger.info(f"📉 [SmartBrain] Penalidade Q-Learning para Estratégia #{strategy_id}: {current:.2f} -> {self.weights[sid]:.2f}")
        
        self.save_weights()


class SessionMemoryRAG:
    """
    RAG de Memória de Sessões. Armazena e recupera comportamentos
    de sessões passadas com distribuições semelhantes de terminais.
    """
    def __init__(self, file_path: str = "data/session_memory_rag.json"):
        self.file_path = file_path
        self.sessions: List[Dict] = []
        self.load_database()

    def load_database(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.sessions = json.load(f)
            except Exception as e:
                logger.warning(f"Erro ao carregar banco RAG: {e}")
                self.sessions = []
        
        # Cria banco RAG inicial caso vazio
        if not self.sessions:
            self._create_mock_sessions()

    def _create_mock_sessions(self):
        # Perfis simulados de referência para busca inicial
        self.sessions = [
            {
                "session_id": "profile_stable_low_terminals",
                "terminals_freq": [15, 8, 5, 8, 12, 10, 8, 10, 12, 12],
                "avg_win_rate": 0.88,
                "description": "Mercado estável com dominância de terminais baixos (T0, T1, T4)"
            },
            {
                "session_id": "profile_high_entropy_messy",
                "terminals_freq": [10, 10, 10, 10, 10, 10, 10, 10, 10, 10],
                "avg_win_rate": 0.65,
                "description": "Alta entropia, distribuição totalmente uniforme e caótica de terminais"
            },
            {
                "session_id": "profile_cluster_geometric",
                "terminals_freq": [5, 12, 15, 12, 8, 5, 12, 15, 8, 8],
                "avg_win_rate": 0.82,
                "description": "Sessão com forte atração geométrica nos setores do zero e vizinhos"
            }
        ]
        self.save_database()

    def save_database(self):
        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.sessions, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Erro ao salvar banco RAG: {e}")

    def save_current_session_profile(self, session_id: str, history: List[int], win_rate: float):
        """Salva o perfil da sessão corrente para aprendizado permanente."""
        if not history:
            return
            
        terminals = [0] * 10
        for num in history:
            terminals[num % 10] += 1
            
        # Normaliza frequências
        total = sum(terminals)
        if total > 0:
            terminals_norm = [int(round((t / total) * 100)) for t in terminals]
        else:
            terminals_norm = [10] * 10

        profile = {
            "session_id": session_id,
            "terminals_freq": terminals_norm,
            "avg_win_rate": win_rate,
            "description": f"Sessão real registrada com {len(history)} giros."
        }
        
        # Evita duplicar sessão
        self.sessions = [s for s in self.sessions if s["session_id"] != session_id]
        self.sessions.append(profile)
        self.save_database()
        logger.info(f"💾 [SmartBrain] Perfil de sessão '{session_id}' salvo com sucesso no RAG.")

    def query_similar_session_winrate(self, current_history: List[int]) -> float:
        """
        Calcula similaridade de cosseno entre a sessão atual e sessões passadas.
        Retorna a assertividade esperada do perfil similar como calibrador.
        """
        if not current_history or len(current_history) < 15:
            return 0.80 # Assertividade neutra padrão
            
        current_terminals = [0] * 10
        for num in current_history:
            current_terminals[num % 10] += 1
            
        best_similarity = -1.0
        best_winrate = 0.80
        best_profile_desc = "Nenhum perfil"
        
        for sess in self.sessions:
            ref_terminals = sess["terminals_freq"]
            
            # Similaridade de Cosseno
            dot_product = sum(a * b for a, b in zip(current_terminals, ref_terminals))
            norm_a = math.sqrt(sum(a**2 for a in current_terminals))
            norm_b = math.sqrt(sum(b**2 for b in ref_terminals))
            
            if norm_a > 0 and norm_b > 0:
                similarity = dot_product / (norm_a * norm_b)
            else:
                similarity = 0.0
                
            if similarity > best_similarity:
                best_similarity = similarity
                best_winrate = sess["avg_win_rate"]
                best_profile_desc = sess["description"]

        logger.info(
            f"🧠 [SmartBrain] Similaridade RAG: perfil '{best_profile_desc}' "
            f"identificado com {best_similarity*100:.1f}% de compatibilidade. Assertividade base esperada: {best_winrate*100:.1f}%"
        )
        return best_winrate


class SmartBrain:
    """Cérebro unificado que encapsula as evoluções físicas e matemáticas."""
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, profiles_path: str = "data/croupier_profiles.json"):
        if not hasattr(self, "initialized"):
            # Lock reentrante: a busca de estratégia agora roda numa thread
            # separada (AsyncStrategySearcher) enquanto a thread principal pode
            # tocar os mesmos objetos no win/loss. Protege o dict de crupiês
            # contra "dict changed size during iteration" e inserções em corrida.
            self._lock = threading.RLock()
            self.profiles_path = profiles_path
            self.croupiers: Dict[str, CroupierSignatureTracker] = {}
            self.q_learning = MesaQLearning()
            self.rag = SessionMemoryRAG()
            self.initialized = True
            self.load_croupier_profiles()

    def sync_croupier_history(self, name: str, history: list):
        """Reseta e repopula o histórico do tracker de um crupiê (thread-safe).
        Usado pelo worker de IA para alimentar a assinatura geométrica."""
        with self._lock:
            tracker = self.get_croupier_tracker(name)
            tracker.history = []
            for num in history[-15:]:
                tracker.add_spin(num)
            return tracker

    def load_croupier_profiles(self):
        if os.path.exists(self.profiles_path):
            try:
                with open(self.profiles_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for name, hist in data.items():
                        tracker = CroupierSignatureTracker()
                        tracker.history = hist
                        self.croupiers[name] = tracker
            except Exception as e:
                logger.warning(f"Erro ao carregar perfis de crupiês: {e}")

    def save_croupier_profiles(self):
        try:
            os.makedirs(os.path.dirname(self.profiles_path), exist_ok=True)
            # Snapshot sob lock: evita "dict changed size during iteration" se o
            # worker de IA inserir um crupiê novo durante o salvamento.
            with self._lock:
                data = {name: list(tracker.history) for name, tracker in self.croupiers.items()}
            with open(self.profiles_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Erro ao salvar perfis de crupiês: {e}")

    def get_croupier_tracker(self, name: str) -> CroupierSignatureTracker:
        name = name.strip() or "Default"
        with self._lock:
            if name not in self.croupiers:
                self.croupiers[name] = CroupierSignatureTracker()
            return self.croupiers[name]

    def calculate_kelly_fraction(self, confidence: int) -> float:
        """
        Calcula a porcentagem recomendada de aposta baseado no critério de Kelly Fracionário.
        b (retorno líquido de aposta com 1 vizinho): cobrimos 3 números de 37.
        A odd média é 35 para 3 = 11.67x o valor apostado, logo b = 10.67.
        """
        p = confidence / 100.0
        b = 10.67
        q = 1.0 - p
        
        if p <= 0:
            return 0.5
            
        # Fração de Kelly Simples
        f_star = (p * b - q) / b
        
        if f_star <= 0:
            return 0.5  # Mínimo padrão de segurança (0.5% da banca)
            
        # Kelly Fracionário (10% de f_star para conservadorismo máximo contra ruína)
        fractional_kelly = f_star * 0.10 * 100
        
        # Limita a sugestão entre 0.5% e 3.0% da banca
        return max(0.5, min(3.0, round(fractional_kelly, 2)))
