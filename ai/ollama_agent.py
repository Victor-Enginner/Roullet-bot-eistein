"""
Agente de IA local usando Ollama para análise de padrões de roleta.

Funcionalidades:
- Conecta ao Ollama local (http://localhost:11434)
- Analisa contexto de jogo (histórico, estratégia, estatísticas)
- Retorna decisão estruturada (JSON) com confidence e reasoning
- Fallback automático: se Ollama falhar, retorna None (caller usa lógica clássica)
- Cache simples para evitar chamadas repetidas com mesmo input
- Timeout configurável para não bloquear o bot
"""

from __future__ import annotations

import json
import logging
import time
import hashlib
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List

try:
    # Biblioteca oficial do Ollama
    from ollama import Client
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    Client = None  # type: ignore

from utils.logger import setup_logger

logger = setup_logger("ai.ollama_agent")


# ---------------------------------------------------------------------------
# Modelo de resposta
# ---------------------------------------------------------------------------

@dataclass
class AIResponse:
    """Resposta estruturada do agente de IA."""
    should_enter: bool
    confidence: int           # 0-100
    reasoning: str            # máx 300 chars
    alternative_targets: List[int]  # opcional
    risk_level: str           # "low" | "medium" | "high"
    raw: Optional[Dict[str, Any]] = None  # resposta crua do LLM

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Prompt de sistema (instruções de comportamento do modelo)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Você é um analista estatístico e físico de sistemas caóticos especializado em roleta europeia (0-36).

Sua tarefa é analisar o fluxo de dados históricos (números passados), o estado atual do mercado (frequência de terminais, desvios da média) e o retrospecto da estratégia sugerida para emitir um parecer probabilístico estritamente técnico em JSON.

REGRAS DE ANÁLISE PROBABILÍSTICA:
1. ANÁLISE DE VARIÂNCIA E CLUSTERS: Identifique se o histórico recente apresenta agrupamentos estatísticos consistentes (desvios temporários da curva de distribuição normal, como densidade de terminais específicos ou vizinhos geométricos do cilindro).
2. MEMÓRIA DE TRANSIÇÃO (MARKOV): Avalie a força da conexão entre o número atual e o padrão estratégico proposto, considerando se há tração no curto prazo ou se a volatilidade local indica dispersão.
3. ENTROPIA DE SESSÃO: Analise a desordem do mercado (grau de bagunça dos terminais recentes). Alta desordem (entropia elevada) aumenta o risco e deve rebaixar a confiança.
4. HISTÓRICO DO GATILHO: Verifique a taxa de acerto acumulada da base (greens vs losses). Bases com retrospecto instável ou perdas recentes exigem cautela extrema.
5. OBJETIVIDADE: Sua análise deve ser baseada em dados reais fornecidos no prompt, sem incentivar jogos de azar.

FORMATO DE RESPOSTA (JSON estrito, sem markdown):
{
  "should_enter": <bool>,
  "confidence": <inteiro 0-100>,
  "reasoning": "<máx 120 caracteres, 1 frase objetiva em português justificando o risco/densidade estatística>",
  "alternative_targets": [<lista de inteiros 0-36, pode ser vazia, contendo vizinhos geométricos ou terminais quentes alinhados>],
  "risk_level": "<low|medium|high>"
}

CRITÉRIOS DE CONFIDENCE:
- 85-100: Densidade estatística forte (clusters quentes alinhados), baixa entropia, base com histórico altamente positivo.
- 60-84:  Condições favoráveis de mercado, sem anomalias graves ou perdas recentes na base.
- 40-59:  Volatilidade média ou base com retrospecto misto (equilíbrio entre perdas e ganhos).
- 0-39:   Não recomendado (alta entropia/desordem nos terminais, perdas recorrentes ou ausência completa de tração estatística).
"""


# ---------------------------------------------------------------------------
# Construção do prompt do usuário
# ---------------------------------------------------------------------------

def _build_user_prompt(
    history_tail: List[int],
    base: int,
    strategy: Dict[str, Any],
    stats: Dict[str, int],
    analysis: Dict[str, Any],
    current_number: int,
    rag_context: Optional[str] = None,
) -> str:
    """Monta o prompt com os dados de mercado para o LLM analisar."""

    # Top 5 hot/cold numbers
    hot = ", ".join(f"{n}({c}x)" for n, c in analysis.get("hot_numbers", [])[:5]) or "n/d"
    cold = ", ".join(f"{n}({c}x)" for n, c in analysis.get("cold_numbers", [])[:5]) or "n/d"

    # Top 3 terminais dominantes
    term_dom = analysis.get("terminal_dominance", {})
    if term_dom:
        top_terms = sorted(term_dom.items(), key=lambda kv: kv[1], reverse=True)[:3]
        terms_str = ", ".join(f"T{t}({c}x)" for t, c in top_terms)
    else:
        terms_str = "n/d"

    # Histórico recente formatado
    hist_str = " → ".join(str(n) for n in history_tail[-30:])

    entrada = strategy.get("entrada") or "(sem entrada)"
    cobertura = strategy.get("cobertura") or "(sem cobertura)"

    # Contexto semântico do RAG de memória de sessões (SPRINT 4). Texto real
    # recuperado da sessão passada mais similar (não um escalar isolado).
    # Opcional: se não vier, o bloco simplesmente não aparece no prompt.
    rag_block = f"\nMEMÓRIA DE SESSÕES SIMILARES (RAG):\n{rag_context}\n" if rag_context else ""

    return f"""DADOS DE MERCADO (roleta europeia):

NÚMERO ATUAL: {current_number}
NÚMERO BASE (gatilho da estratégia): {base}

ÚLTIMOS {len(history_tail)} GIROS:
{hist_str}

ESTRATÉGIA CADASTRADA PARA BASE {base}:
- Leitura: {strategy.get("leitura", "n/d")}
- Entrada: {entrada}
- Cobertura: {cobertura}

ESTATÍSTICAS DESTA BASE (histórico acumulado):
- Greens diretos: {stats.get("directGreen", 0)}
- Greens por proteção: {stats.get("protectionGreen", 0)}
- Losses: {stats.get("loss", 0)}
- Total operações: {sum(stats.values())}

ANÁLISE DE MERCADO (últimos 500 giros):
- Números quentes: {hot}
- Números frios: {cold}
- Terminais dominantes: {terms_str}
{rag_block}
Analise e responda em JSON conforme o formato definido."""


# ---------------------------------------------------------------------------
# Parser de resposta (robusto contra pequenas variações do LLM)
# ---------------------------------------------------------------------------

def _parse_llm_response(text: str) -> Optional[AIResponse]:
    """Extrai JSON da resposta do LLM, tolerando pequenos desvios."""

    if not text:
        return None

    text = text.strip()

    # Remove markdown ```json ... ``` se o modelo adicionar
    if "```" in text:
        try:
            # Pega o conteúdo entre ```json e ```
            parts = text.split("```")
            for i, p in enumerate(parts):
                if "json" in p.lower() or "{" in p:
                    candidate = p.replace("json", "", 1).strip()
                    if candidate.startswith("{"):
                        text = candidate
                        break
        except Exception:
            pass

    # Tenta parsear direto
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Tenta encontrar o primeiro JSON válido no texto
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                logger.warning(f"IA retornou JSON inválido: {text[:200]}")
                return None
        else:
            logger.warning(f"IA não retornou JSON: {text[:200]}")
            return None

    # Validação e normalização
    try:
        should_enter = bool(data.get("should_enter", False))
        confidence = int(data.get("confidence", 0))
        confidence = max(0, min(100, confidence))
        reasoning = str(data.get("reasoning", "")).strip()[:300]
        alt_targets = data.get("alternative_targets", []) or []
        if not isinstance(alt_targets, list):
            alt_targets = []
        alt_targets = [int(n) for n in alt_targets if isinstance(n, (int, float)) and 0 <= int(n) <= 36]
        risk_level = str(data.get("risk_level", "medium")).lower()
        if risk_level not in ("low", "medium", "high"):
            risk_level = "medium"

        return AIResponse(
            should_enter=should_enter,
            confidence=confidence,
            reasoning=reasoning,
            alternative_targets=alt_targets,
            risk_level=risk_level,
            raw=data,
        )
    except Exception as e:
        logger.warning(f"Erro ao normalizar resposta da IA: {e}")
        return None


# ---------------------------------------------------------------------------
# Agente principal
# ---------------------------------------------------------------------------

class OllamaAnalyst:
    """
    Agente de análise via Ollama local.

    Uso:
        analyst = OllamaAnalyst(model="llama3.1:8b")
        opinion = analyst.analyze(
            history=history[-100:],
            base=23,
            strategy=ESTRATEGIAS[23],
            stats=memory.get_stats(23),
            analysis=analyze_recent(history),
            current_number=23,
        )
        if opinion and opinion.should_enter:
            # usa opinion.confidence e opinion.reasoning
            ...
    """

    def __init__(
        self,
        model: Optional[str | List[str]] = None,
        host: str = "http://127.0.0.1:11434",
        timeout: float = 20.0,
        enabled: bool = True,
        min_confidence: int = 30,
        cache_ttl: int = 60,
    ):
        """
        Args:
            model:        Nome do modelo Ollama ou lista de modelos de prioridade
            host:         URL do servidor Ollama
            timeout:      Timeout em segundos para cada chamada
            enabled:      Se False, analyze() sempre retorna None (fallback)
            min_confidence: Confiança mínima pra considerar "should_enter=True"
            cache_ttl:    Tempo (s) de cache de respostas idênticas
        """
        import os
        if model is None:
            env_model = os.getenv("OLLAMA_MODEL")
            if env_model:
                self.models = [env_model]
            else:
                self.models = [
                    "qwen2.5:1.5b",
                    "llama3.2:1b",
                    "gemma2:2b",
                    "llama3.2:3b",
                    "llama3.1:8b",
                    "llama3:latest"
                ]
        else:
            self.models = [model] if isinstance(model, str) else model

        self.model = self.models[0]
        self.host = host
        # Timeout configurável por env. O DEFAULT (20s) precisa ser MAIOR que o
        # cold start do modelo na CPU (~6s no i7-3770S) — senão o preload e a 1ª
        # chamada morrem antes do modelo terminar de carregar e a IA NUNCA aquece.
        env_timeout = os.getenv("OLLAMA_TIMEOUT")
        self.timeout = float(env_timeout) if env_timeout else timeout
        self.enabled = enabled
        self.min_confidence = min_confidence
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, tuple] = {}  # hash -> (timestamp, AIResponse)
        self._client: Optional["Client"] = None
        self._available: Optional[bool] = None  # testado lazy
        self._last_failure_time: float = 0.0
        self._failure_cooldown: float = 60.0  # seconds

        if not OLLAMA_AVAILABLE:
            logger.warning(
                "⚠️ Biblioteca 'ollama' não instalada. "
                "Rode: pip install ollama"
            )

    # ----- Setup -----

    def _get_client(self) -> Optional["Client"]:
        if not OLLAMA_AVAILABLE:
            return None
        if self._client is None:
            try:
                self._client = Client(host=self.host, timeout=self.timeout)
            except Exception as e:
                logger.error(f"Falha ao criar cliente Ollama: {e}")
                return None
        return self._client

    def is_available(self) -> bool:
        """Testa se Ollama está rodando e o modelo está disponível."""
        if not self.enabled or not OLLAMA_AVAILABLE:
            return False
        # OTIMIZAÇÃO: se já confirmamos disponibilidade, NÃO refaz client.list()
        # a cada análise (isso era um round-trip HTTP extra no hot path antes
        # de toda inferência). Uma falha real em analyze() reseta _available.
        if self._available is True:
            return True
        if self._available is False:
            if time.time() - self._last_failure_time < self._failure_cooldown:
                return False
            # Cooldown de falha expirou, tenta novamente
            self._available = None
            logger.info("🔄 Cooldown de falha do Ollama expirou. Tentando reconectar...")
        client = self._get_client()
        if client is None:
            self._available = False
            self._last_failure_time = time.time()
            return False
        try:
            # list() é leve e confirma conexão
            client.list()
            self._available = True
            return True
        except Exception as e:
            logger.debug(f"Ollama indisponível: {e}")
            self._available = False
            self._last_failure_time = time.time()
            return False

    def preload(self) -> None:
        """Carrega o modelo na GPU/memória sem fazer uma análise real."""
        if not self.enabled or not self.is_available():
            return
        client = self._get_client()
        if client is None:
            return
        try:
            logger.info(f"🧠 Pré-carregando o modelo {self.model} na GPU...")
            client.chat(
                model=self.model,
                messages=[{"role": "user", "content": "hello"}],
                options={"num_predict": 1},
                keep_alive=-1,
            )
            logger.info(f"✅ Modelo {self.model} pré-carregado com sucesso na GPU.")
        except Exception as e:
            logger.warning(f"Não foi possível pré-carregar o modelo: {e}")

    # ----- Cache -----

    def _cache_key(self, base: int, history_tail: List[int], rag_context: Optional[str] = None) -> str:
        # Hash dos últimos 10 números + base + contexto RAG (se houver)
        sample = ",".join(str(n) for n in history_tail[-10:])
        rag_part = rag_context or ""
        return hashlib.md5(f"{base}|{sample}|{rag_part}".encode()).hexdigest()

    def _get_cached(self, key: str) -> Optional[AIResponse]:
        if key in self._cache:
            ts, resp = self._cache[key]
            if time.time() - ts < self.cache_ttl:
                return resp
            else:
                del self._cache[key]
        return None

    def _set_cached(self, key: str, resp: AIResponse) -> None:
        self._cache[key] = (time.time(), resp)
        # Limpa cache se ficar muito grande
        if len(self._cache) > 200:
            now = time.time()
            self._cache = {
                k: v for k, v in self._cache.items() if now - v[0] < self.cache_ttl
            }

    # ----- Análise principal -----

    def analyze(
        self,
        history: List[int],
        base: int,
        strategy: Dict[str, Any],
        stats: Dict[str, int],
        analysis: Dict[str, Any],
        current_number: Optional[int] = None,
        rag_context: Optional[str] = None,
    ) -> Optional[AIResponse]:
        """
        Consulta o LLM e devolve uma AIResponse ou None em caso de falha.

        Args:
            rag_context: texto opcional recuperado do RAG de memória de
                sessões (ai.smart_brain.SessionMemoryRAG.query_similar_session_context)
                com a descrição real da sessão passada mais similar. Se
                fornecido, é injetado como contexto adicional no prompt.

        Retorna None se:
        - enabled=False
        - Ollama indisponível
        - Timeout / erro de rede
        - Resposta inválida

        Nesses casos, o caller deve usar a lógica clássica.
        """
        if not self.enabled:
            return None

        if not self.is_available():
            return None

        current_number = current_number if current_number is not None else base
        history_tail = history[-50:] if len(history) > 50 else history

        # Verifica cache (inclui o contexto RAG na chave: um contexto novo
        # pode mudar a análise mesmo com o mesmo histórico recente)
        cache_key = self._cache_key(base, history_tail, rag_context)
        cached = self._get_cached(cache_key)
        if cached is not None:
            logger.debug(f"IA: cache hit para base {base}")
            return cached

        user_prompt = _build_user_prompt(
            history_tail=history_tail,
            base=base,
            strategy=strategy,
            stats=stats,
            analysis=analysis,
            current_number=current_number,
            rag_context=rag_context,
        )

        client = self._get_client()
        if client is None:
            return None

        start = time.time()
        try:
            response = None
            last_err = None
            
            for active_model in self.models:
                try:
                    logger.debug(f"IA: tentando consultar o modelo '{active_model}'...")
                    response = client.chat(
                        model=active_model,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        format="json",
                        options={
                            "temperature": 0.1,    # mais determinístico e rápido
                            "num_predict": 160,    # margem p/ o JSON fechar mesmo se o modelo ignorar o limite de chars (evita None)
                            "top_p": 0.9,
                            "top_k": 20,           # reduz o espaço de amostragem -> menos cálculo por token
                            "num_ctx": 1536,       # contexto enxuto = prefill mais rápido
                            "stop": ["```"],       # NÃO usar "}\n" como stop (cortava o JSON antes do fim)
                        },
                        keep_alive=-1,  # mantém modelo na GPU/memória indefinidamente
                    )
                    # Se respondeu com sucesso, atualiza o modelo ativo e sai do loop
                    self.model = active_model
                    break
                except Exception as e:
                    logger.warning(f"Ollama modelo '{active_model}' falhou: {e}")
                    last_err = e
                    continue
                    
            if response is None:
                raise last_err or Exception("Todos os modelos da lista de backups falharam.")

            elapsed = time.time() - start
            text = response.get("message", {}).get("content", "")
            logger.info(f"🧠 IA respondeu em {elapsed:.2f}s (modelo: {self.model}) para base {base}")

            ai_resp = _parse_llm_response(text)
            if ai_resp is None:
                return None

            # Aplica filtro mínimo de confiança
            if ai_resp.confidence < self.min_confidence:
                ai_resp.should_enter = False
                logger.debug(
                    f"IA: confiança {ai_resp.confidence} < {self.min_confidence} → forçando should_enter=False"
                )

            self._set_cached(cache_key, ai_resp)
            return ai_resp

        except Exception as e:
            elapsed = time.time() - start
            logger.warning(f"⚠️ IA falhou após {elapsed:.2f}s: {e}")
            self._available = False  # evita tentar de novo por um tempo
            return None

    def get_stats_summary(self) -> Dict[str, Any]:
        """Estatísticas de uso do agente (debug/telemetria)."""
        return {
            "model": self.model,
            "host": self.host,
            "enabled": self.enabled,
            "available": self._available,
            "cache_size": len(self._cache),
            "min_confidence": self.min_confidence,
        }


# ---------------------------------------------------------------------------
# Factory de conveniência
# ---------------------------------------------------------------------------

_default_analyst: Optional[OllamaAnalyst] = None


def get_analyst() -> OllamaAnalyst:
    """Retorna instância singleton do analista."""
    global _default_analyst
    if _default_analyst is None:
        _default_analyst = OllamaAnalyst()
    return _default_analyst
