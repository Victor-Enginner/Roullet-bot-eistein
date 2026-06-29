"""
Buscador de estratégia ASSÍNCRONO (single-flight).

Por que existe:
    run_engine() consulta a IA local (Ollama), que pode levar ~0.5-2s. Rodar
    isso DENTRO do loop principal travava a detecção do próximo número.

Como resolve o gargalo sem criar corrida de estado:
    - submit() dispara run_engine() numa thread de trabalho e RETORNA na hora.
      O loop principal nunca bloqueia esperando a IA.
    - O resultado é depositado num slot protegido por lock (padrão
      produtor/consumidor).
    - poll() é chamado pelo loop principal (thread principal). TODA mutação de
      estado da aposta (strategy_state.activate, envio de sinal) acontece na
      thread principal, ao consumir o resultado -> ZERO race condition.
    - single-flight: enquanto uma busca está em andamento, novas submissões são
      ignoradas (não adianta empilhar IA para o mesmo intervalo de giros).
"""

import threading

from server.services.engine import run_engine


class AsyncStrategySearcher:
    def __init__(self):
        self._lock = threading.Lock()
        self._busy = False
        self._result = None  # tupla (base:int, signal:dict) aguardando consumo

    @property
    def busy(self) -> bool:
        with self._lock:
            return self._busy

    def submit(self, history, base, dealer, memory_agent) -> bool:
        """Dispara uma busca em background. Retorna False se já há uma rodando
        ou um resultado ainda não consumido (single-flight)."""
        with self._lock:
            if self._busy or self._result is not None:
                return False
            self._busy = True

        # Snapshot do histórico: evita que o worker leia uma lista sendo mutada
        # pela thread principal enquanto roda.
        history_snapshot = list(history)

        def _worker():
            signal = None
            try:
                signal = run_engine(
                    history=history_snapshot,
                    memory_agent=memory_agent,
                    base=base,
                    dealer=dealer,
                )
            except Exception:
                signal = None
            finally:
                with self._lock:
                    self._result = (base, signal)
                    self._busy = False

        threading.Thread(target=_worker, daemon=True).start()
        return True

    def poll(self):
        """Devolve (base, signal) pronto para consumo, ou None. Consome o slot."""
        with self._lock:
            r = self._result
            self._result = None
            return r
