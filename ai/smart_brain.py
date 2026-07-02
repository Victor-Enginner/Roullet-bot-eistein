import math
import json
import os
import logging
import threading
import time
from typing import List, Dict, Optional, Tuple

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None  # type: ignore

from config.settings import Settings

logger = logging.getLogger("ai.smart_brain")

# Config de embeddings via Ollama local (SPRINT 4 — RAG semântico real).
RAG_EMBEDDING_MODEL = Settings.RAG_EMBEDDING_MODEL
RAG_EMBEDDING_HOST = Settings.RAG_EMBEDDING_HOST
RAG_EMBEDDING_TIMEOUT = Settings.RAG_EMBEDDING_TIMEOUT

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

    SPRINT 4: usa embeddings semânticos reais (Ollama local, modelo
    RAG_EMBEDDING_MODEL) gerados a partir de um texto descritivo real da
    sessão (terminais dominantes + estratégias + win rate observado).
    Se o Ollama/modelo de embedding não estiver disponível, cai de volta
    (fallback) para a heurística antiga de similaridade de cosseno sobre o
    vetor de 10 frequências de terminais — o bot NUNCA deve quebrar por
    falta de um modelo de embedding local.

    Nunca mistura dado inventado/mockado com dado real de sessão no cálculo
    de confiança: o banco só contém sessões efetivamente registradas pelo
    bot (save_current_session_profile). Se não houver nenhuma sessão real
    ainda, a consulta retorna a assertividade neutra padrão (0.80) em vez
    de inventar um "perfil de referência".
    """
    def __init__(self, file_path: str = "data/session_memory_rag.json"):
        self.file_path = file_path
        self.sessions: List[Dict] = []
        self._embedding_fallback_logged = False
        # Cooldown de falha: se o endpoint de embeddings do Ollama falhar
        # (fora do ar, sem o modelo, etc.), evita tentar de novo a cada
        # consulta/salvamento de sessão — isso adicionaria latência de rede
        # (timeout) a cada chamada num bot que roda em tempo real.
        self._embedding_unavailable_since: float = 0.0
        self._embedding_failure_cooldown: float = 300.0  # 5 minutos
        self.load_database()

    def load_database(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.sessions = json.load(f)
            except Exception as e:
                logger.warning(f"Erro ao carregar banco RAG: {e}")
                self.sessions = []

        # SEM dados mockados: se o banco estiver vazio, permanece vazio até
        # que sessões reais sejam registradas. Misturar perfis inventados
        # com sessões reais no mesmo cálculo de similaridade contaminaria a
        # confiança reportada ao bot (ver auditoria da SPRINT 4).

    def save_database(self):
        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.sessions, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Erro ao salvar banco RAG: {e}")

    # ----- Texto descritivo real da sessão -----

    def _build_session_text(
        self,
        history: List[int],
        win_rate: float,
        terminals_norm: List[int],
        strategies_used: Optional[List[str]] = None,
    ) -> str:
        """Monta um texto descritivo real da sessão (para embedding semântico),
        combinando terminais mais frequentes, estratégias usadas e win rate real
        observado — em vez do vetor cru de 10 números."""
        ranked_terms = sorted(range(10), key=lambda t: terminals_norm[t], reverse=True)
        top_terms = ", ".join(f"T{t}({terminals_norm[t]}%)" for t in ranked_terms[:3])

        if strategies_used:
            strategies_str = ", ".join(strategies_used[:5])
        else:
            strategies_str = "n/d"

        return (
            f"Sessão de roleta com {len(history)} giros registrados. "
            f"Terminais dominantes: {top_terms}. "
            f"Estratégias utilizadas: {strategies_str}. "
            f"Win rate real observado: {win_rate * 100:.1f}%."
        )

    # ----- Embeddings via Ollama (com fallback heurístico obrigatório) -----

    def _get_ollama_embedding(self, text: str) -> Optional[List[float]]:
        """Tenta gerar um embedding real via Ollama local. Retorna None (sem
        levantar exceção) se o endpoint não responder ou o modelo não existir
        localmente — quem chamar deve cair no fallback heurístico antigo.
        Loga o modo fallback apenas uma vez para não poluir o log do bot.

        Respeita um cooldown de falha: se a última tentativa falhou há menos
        de _embedding_failure_cooldown segundos, nem tenta de novo (evita
        pagar o custo de timeout de rede a cada consulta/salvamento de sessão
        enquanto o Ollama/modelo estiver fora do ar)."""
        if not REQUESTS_AVAILABLE:
            self._log_embedding_fallback_once("biblioteca 'requests' indisponível")
            return None

        if self._embedding_unavailable_since > 0:
            if time.time() - self._embedding_unavailable_since < self._embedding_failure_cooldown:
                return None
            # Cooldown expirou: tenta de novo silenciosamente

        try:
            resp = requests.post(
                f"{RAG_EMBEDDING_HOST}/api/embeddings",
                json={"model": RAG_EMBEDDING_MODEL, "prompt": text},
                timeout=RAG_EMBEDDING_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            embedding = data.get("embedding")
            if not embedding or not isinstance(embedding, list):
                self._log_embedding_fallback_once(
                    f"resposta do Ollama sem campo 'embedding' válido (modelo '{RAG_EMBEDDING_MODEL}')"
                )
                self._mark_embedding_unavailable()
                return None
            # Sucesso: limpa qualquer cooldown de falha anterior
            self._embedding_unavailable_since = 0.0
            return embedding
        except Exception as e:
            self._log_embedding_fallback_once(
                f"Ollama/embeddings indisponível ou modelo '{RAG_EMBEDDING_MODEL}' não encontrado: {e}"
            )
            self._mark_embedding_unavailable()
            return None

    def _mark_embedding_unavailable(self):
        self._embedding_unavailable_since = time.time()

    def _log_embedding_fallback_once(self, reason: str):
        if not self._embedding_fallback_logged:
            logger.info(
                f"🧠 [SmartBrain] RAG em modo fallback heurístico (sem embeddings semânticos). "
                f"Motivo: {reason}. Usando similaridade de cosseno sobre frequência de terminais."
            )
            self._embedding_fallback_logged = True

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x**2 for x in a))
        norm_b = math.sqrt(sum(y**2 for y in b))
        if norm_a > 0 and norm_b > 0:
            return dot_product / (norm_a * norm_b)
        return 0.0

    def save_current_session_profile(
        self,
        session_id: str,
        history: List[int],
        win_rate: float,
        strategies_used: Optional[List[str]] = None,
    ):
        """Salva o perfil da sessão corrente para aprendizado permanente.
        Persiste o texto descritivo real e, quando possível, o embedding
        semântico real gerado via Ollama junto com a sessão."""
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

        session_text = self._build_session_text(history, win_rate, terminals_norm, strategies_used)
        embedding = self._get_ollama_embedding(session_text)

        profile = {
            "session_id": session_id,
            "terminals_freq": terminals_norm,
            "avg_win_rate": win_rate,
            "description": f"Sessão real registrada com {len(history)} giros.",
            "session_text": session_text,
            "embedding": embedding,  # None se o Ollama/modelo não estava disponível
            "embedding_model": RAG_EMBEDDING_MODEL if embedding is not None else None,
        }

        # Evita duplicar sessão
        self.sessions = [s for s in self.sessions if s["session_id"] != session_id]
        self.sessions.append(profile)
        self.save_database()
        logger.info(f"💾 [SmartBrain] Perfil de sessão '{session_id}' salvo com sucesso no RAG.")

    def query_similar_session_context(
        self, current_history: List[int]
    ) -> Tuple[float, str]:
        """
        Recupera a sessão mais similar à sessão atual e retorna tanto a
        assertividade (win rate) esperada quanto o TEXTO descritivo da(s)
        sessão(ões) similares, para injeção como contexto adicional no
        prompt do LLM (ai/ollama_agent.py).

        Tenta comparar por embedding semântico real (Ollama) quando a sessão
        atual e as sessões salvas possuem embedding; cai de volta para a
        heurística de cosseno sobre frequência de terminais caso contrário.
        """
        if not current_history or len(current_history) < 15:
            return 0.80, "Sem contexto de sessões similares (histórico insuficiente)."

        if not self.sessions:
            return 0.80, "Nenhuma sessão real registrada ainda no RAG."

        current_terminals = [0] * 10
        for num in current_history:
            current_terminals[num % 10] += 1
        total = sum(current_terminals)
        current_terminals_norm = (
            [int(round((t / total) * 100)) for t in current_terminals] if total > 0 else [10] * 10
        )
        current_text = self._build_session_text(current_history, 0.0, current_terminals_norm)
        current_embedding = self._get_ollama_embedding(current_text)

        best_similarity = -1.0
        best_session: Optional[Dict] = None
        use_embeddings = current_embedding is not None

        for sess in self.sessions:
            ref_embedding = sess.get("embedding")
            if use_embeddings and ref_embedding:
                similarity = self._cosine_similarity(current_embedding, ref_embedding)
            else:
                # Fallback heurístico: vetor de 10 terminais + cosseno
                ref_terminals = sess.get("terminals_freq", [])
                similarity = self._cosine_similarity(
                    [float(x) for x in current_terminals], [float(x) for x in ref_terminals]
                )

            if similarity > best_similarity:
                best_similarity = similarity
                best_session = sess

        if best_session is None:
            return 0.80, "Nenhum perfil similar encontrado."

        best_winrate = best_session.get("avg_win_rate", 0.80)
        best_text = best_session.get("session_text") or best_session.get("description", "")
        mode = "embedding semântico" if (use_embeddings and best_session.get("embedding")) else "heurística de terminais"

        logger.info(
            f"🧠 [SmartBrain] Similaridade RAG ({mode}): sessão '{best_session.get('session_id')}' "
            f"identificada com {best_similarity*100:.1f}% de compatibilidade. Assertividade base esperada: {best_winrate*100:.1f}%"
        )

        context_text = (
            f"[Memória RAG] Sessão passada mais similar ({best_similarity*100:.0f}% compatível): {best_text}"
        )
        return best_winrate, context_text

    def query_similar_session_winrate(self, current_history: List[int]) -> float:
        """
        Retorna apenas a assertividade (win rate) esperada da sessão mais
        similar. Mantido para compatibilidade com chamadores existentes
        (ex.: server/services/engine.py) que só precisam do escalar.
        Internamente usa a mesma lógica de query_similar_session_context.
        """
        winrate, _ = self.query_similar_session_context(current_history)
        return winrate


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
