import time
import sys
from datetime import datetime

from config.settings import Settings
from core.monitor import GameMonitor
from engine import (
    StrategyState,
    pre_process_strategies,
    get_optimized_strategy,
    ESTRATEGIAS,
)
from services.bot import TelegramBot
from services.reporting import ReportingSystem
from storage.database import Database
from analytics.metrics import Metrics, HealthMonitor
from analytics.strategy_analytics import analytics
from analytics.context_filter import ContextFilter
from analytics.strategy_performance import tracker
from storage.backup import backup_system
from utils.logger import setup_logger
from utils.history_buffer import HistoryBuffer
from utils.turbulence_monitor import TurbulenceMonitor
from analytics.transition_memory import TransitionMemory

# New agentic system
from server.agents.memory import MemoryAgent
from server.services.engine import run_engine
from server.agents.telegram import format_telegram_message

logger = setup_logger("main_visual")


def send_signal_to_bridge(
    number: int,
    strategy: str,
    protection: str,
    leitura: str,
    confidence: float,
    kelly_stake: float = 1.0,
    dealer: str = "Default",
    is_protection: bool = False,
    attempt: int = 0,
    reset: bool = False,
    outcome: str = "",
    status_tick: bool = False
):
    """Envia o sinal estruturado para o bridge local (porta 4000) de forma assíncrona (thread)"""
    import threading
    def _worker():
        import requests
        bridge_url = "http://localhost:4000/api/webhook/signal"
        payload = {
            "number": number,
            "strategy": strategy,
            "protection": protection,
            "leitura": leitura,
            "confidence": confidence,
            "kelly_stake": kelly_stake,
            "dealer": dealer,
            "is_protection": is_protection,
            "attempt": attempt,
            "reset": reset,
            "outcome": outcome,
            "status_tick": status_tick,
            "timestamp": time.time()
        }
        try:
            requests.post(bridge_url, json=payload, timeout=0.5)
        except Exception as e:
            logger.debug(f"Erro ao enviar sinal para o bridge: {e}")
            
    threading.Thread(target=_worker, daemon=True).start()


def run_bot():
    """Execução principal do bot com lógica de sessão"""
    # 1. Menu interativo para seleção de estratégias
    from server.agents.strategy import select_strategy_menu
    select_strategy_menu()

    logger.info("=" * 60)
    logger.info("BOT INICIADO - Roleta Brasileira (Arquitetura Portável)")
    logger.info(f"Database: {Settings.DB_PATH}")
    logger.info("=" * 60)

    # OTIMIZAÇÃO: Pré-processa estratégias
    strategies_count = pre_process_strategies()
    logger.info(f"⚡ Otimização: {strategies_count} estratégias carregadas na memória")

    # OTIMIZAÇÃO: Pré-carrega o modelo Ollama na GPU em segundo plano
    try:
        from server.services.engine import AI_ENABLED
        if AI_ENABLED:
            import threading
            def preload_ollama():
                try:
                    from ai.ollama_agent import get_analyst
                    analyst = get_analyst()
                    analyst.preload()
                except Exception as e:
                    logger.warning(f"Erro ao pré-carregar modelo Ollama: {e}")
            threading.Thread(target=preload_ollama, daemon=True).start()
    except Exception as e:
        logger.warning(f"Falha ao iniciar thread de pré-carregamento da IA: {e}")

    db = Database(str(Settings.DB_PATH))
    session_id = db.start_session()

    # Sistema de Relatórios e Analytics
    reporting = ReportingSystem(db)
    analytics.set_session(session_id)

    # New Agentic Memory
    memory_agent = MemoryAgent()

    metrics = Metrics(start_time=time.time())
    health_monitor = HealthMonitor(metrics)

    # Inicializa Monitor Visual (Abre o navegador)
    monitor = GameMonitor()

    bot = TelegramBot(Settings.TELEGRAM_TOKEN, Settings.TELEGRAM_CHAT_ID)
    strategy_state = StrategyState()
    context_filter = ContextFilter()
    turbulence_monitor = TurbulenceMonitor(bot)

    # Inicia Backup Automático e Listener de Comandos
    backup_system.start()
    bot.start_listener(reporting)

    # NOVAS REGRAS DE INTELIGÊNCIA
    wait_rounds = 0  # Contador de espera após WIN

    # Histórico recente para análise de estabilidade longa (500)
    history_buffer = HistoryBuffer(max_size=500)
    transition_memory = TransitionMemory()

    try:
        if not monitor.start():
            logger.error("Falha ao iniciar monitor. Abortando sessão.")
            return False

        logger.info("Monitor iniciado. Aguardando detecção de números...")

        # OTIMIZAÇÃO: Carrega o histórico inicial visível na tela para preencher o buffer
        initial_history = monitor.get_initial_history()
        if initial_history:
            for num in initial_history:
                history_buffer.add(num, time.time())
            logger.info(f"⚡ Buffer inicializado com {len(initial_history)} giros passados da roleta.")

        stats = db.get_statistics()
        logger.info(f"Estatísticas: {stats['total_numbers']} números salvos")

        last_heartbeat = time.time()

        while True:
            # Captura novo número (Utiliza MutationObserver no container estendido)
            numero_str = monitor.watch()
            if not numero_str:
                time.sleep(1)
                continue

            numero = int(numero_str)
            metrics.numbers_detected += 1
            metrics.last_number_time = time.time()
            logger.info(f"🔥 Novo Número Detectado: {numero}")

            # Atualiza histórico recente (mantém últimos 100 via FIFO)
            if not history_buffer.add(numero, time.time()):
                continue  # Ignora giro inconsistente (Windows 10 integrity)

            # Envia status tick para atualizar Croupier e Último Giro no HUD em tempo real
            active_dealer = monitor.get_current_dealer()
            send_signal_to_bridge(
                number=numero,
                strategy="",
                protection="",
                leitura="",
                confidence=0.0,
                dealer=active_dealer,
                status_tick=True
            )

            # 0. Atualiza memória de transições e detecta padrões (Somente após 60 giros)
            transition_memory.update(history_buffer.get_last(2))
            if len(history_buffer) >= Settings.STATS_WINDOW_SIZE:
                patterns = transition_memory.detect_pattern(numero)
                if patterns and numero in ESTRATEGIAS:
                    lines = "\n".join(
                        f"➡️ {n} ocorreu {x}x"
                        for n, x in sorted(
                            patterns.items(), key=lambda kv: kv[1], reverse=True
                        )[:2]
                    )
                    msg_pattern = (
                        f"📊 PADRÃO SEQUENCIAL DETECTADO\n\n"
                        f"Após o número {numero}:\n\n"
                        f"{lines}\n\n"
                        f"Possível repetição contextual."
                    )
                    bot.enviar_evento("PATTERN", msg_pattern)

            # 1. Registro do número
            db.save_number(numero, telegram_sent=True, strategy=None)

            # 2. Notificação Imediata
            bot.enviar_evento("NEW_NUMBER", f"🎲 Novo número: {numero}", imediato=True)

            # 4. Redução de wait_rounds se houver
            can_search_strategy = True
            if wait_rounds > 0:
                logger.info(
                    f"⏳ Inteligência: Aguardando estabilidade ({wait_rounds} giros restantes)"
                )
                wait_rounds -= 1
                can_search_strategy = False

            # 5. Processamento de Estratégia Ativa
            if strategy_state.active:
                result = strategy_state.process_number(numero)

                if result in ["WIN_ENTRY", "WIN_PROTECTION"]:
                    metrics.green_count += 1
                    total_signals = metrics.green_count + metrics.red_count
                    accuracy = (
                        (metrics.green_count / total_signals) * 100
                        if total_signals > 0
                        else 0
                    )
                    win_type = "NA ENTRADA" if result == "WIN_ENTRY" else "NA PROTEÇÃO"

                    msg = (
                        f"🟢 WIN NO {numero} ({win_type})\n"
                        f"📊 PARTIDAS: 🟢 {metrics.green_count} | 🔴 {metrics.red_count}\n"
                        f"🎯 Taxa de acerto: {accuracy:.1f}%"
                    )
                    logger.info(f"WIN {win_type} detectado no {numero}")
                    send_signal_to_bridge(
                        number=numero,
                        strategy="",
                        protection="",
                        leitura="",
                        confidence=0.0,
                        reset=True,
                        outcome="win"
                    )
                    bot.enviar_evento(result, msg, imediato=True)

                    stats_msg = analytics.register(
                        strategy_state.strategy_id, result, strategy_name="Strategy"
                    )
                    if stats_msg:
                        bot.enviar_evento("ANALYTICS", stats_msg)

                    # --- Analytics de Performance (Novo) ---
                    current_id = strategy_state.strategy_id
                    tracker.register_win(current_id)

                    # Update memory agent
                    result_type = "green" if result == "WIN_ENTRY" else "g1"
                    memory_agent.update_stats(numero, result_type)

                    # Update SmartBrain Q-learning weights
                    try:
                        from ai.smart_brain import SmartBrain
                        SmartBrain().q_learning.register_outcome(current_id, result_type)
                    except Exception as q_err:
                        logger.warning(f"Erro ao registrar Q-Learning no Win: {q_err}")

                    # Alerta de HOT Strategy
                    winrate = tracker.should_notify(current_id)
                    if winrate:
                        msg_hot = (
                            "🔥 ESTRATÉGIA EM ALTA PERFORMANCE\n\n"
                            f"Estratégia Terminal:\nID: {current_id}\n\n"
                            f"📊 Assertividade:\n{winrate:.2f}%\n\n"
                            f"Base: {tracker.stats[current_id]['total']} operações"
                        )
                        bot.enviar_evento("HOT_STRATEGY", msg_hot)

                    strategy_state.reset()
                    # REGRA INTELIGENTE: Aguarda giros após WIN
                    wait_rounds = (
                        Settings.WAIT_ROUNDS_AFTER_ZERO
                        if numero == 0
                        else Settings.WAIT_ROUNDS_AFTER_WIN
                    )
                    logger.info(
                        f"✅ Inteligência: WIN no {numero}. Pausando por {wait_rounds} giros."
                    )

                elif result == "LOSS":
                    metrics.red_count += 1
                    msg = f"🔴 LOSS CONFIRMADO\n❌ 3 proteções atingidas\nEncerrando leitura"
                    logger.info(f"LOSS detectado no {numero}")
                    send_signal_to_bridge(
                        number=numero,
                        strategy="",
                        protection="",
                        leitura="",
                        confidence=0.0,
                        reset=True,
                        outcome="loss"
                    )
                    bot.enviar_evento("LOSS", msg, imediato=True)

                    stats_msg = analytics.register(
                        strategy_state.strategy_id, result, strategy_name="Strategy"
                    )
                    if stats_msg:
                        bot.enviar_evento("ANALYTICS", stats_msg)

                    # --- Analytics de Performance (Novo) ---
                    tracker.register_loss(strategy_state.strategy_id)

                    # Update memory agent
                    memory_agent.update_stats(numero, "loss")

                    # Update SmartBrain Q-learning weights
                    try:
                        from ai.smart_brain import SmartBrain
                        SmartBrain().q_learning.register_outcome(strategy_state.strategy_id, "loss")
                    except Exception as q_err:
                        logger.warning(f"Erro ao registrar Q-Learning no Loss: {q_err}")

                    strategy_state.reset()
                    wait_rounds = 1  # No LOSS aguarda pelo menos 1

                elif result == "PROTECTION":
                    msg = (
                        f"⚠️ Proteção {strategy_state.attempt}/3\nSeguimos na estratégia"
                    )
                    logger.info(f"Proteção {strategy_state.attempt}/3 no {numero}")
                    send_signal_to_bridge(
                        number=numero,
                        strategy="",
                        protection="",
                        leitura="",
                        confidence=0.0,
                        is_protection=True,
                        attempt=strategy_state.attempt
                    )
                    bot.enviar_evento("PROTECTION", msg)
                    time.sleep(0.5)
                    continue

            # 6. Monitoramento de Contexto e Turbulência (Sempre ativo)
            has_turbulence, info = context_filter.should_block_entry(
                history_buffer.get_all(), numero
            )
            if info.get("type") not in ("initializing",) and has_turbulence:
                turbulence_monitor.update(has_turbulence, info)

            # 7. Verificação de Terminais Bagunçados
            history = history_buffer.get_all()
            if len(history) >= 6:
                last6 = history[-6:]
                terminals = [n % 10 for n in last6]
                if len(set(terminals)) == 6:  # Todos terminais diferentes
                    msg_baguncados = "🚨 Terminais bagunçados na mesa!\nÚltimos 6 números com terminais totalmente diferentes."
                    bot.enviar_evento("MESSY_TERMINALS", msg_baguncados, imediato=True)
                    logger.info("Terminais bagunçados detectados.")
                    wait_rounds = 2  # Pausa por 2 giros

            # 8. Busca nova estratégia (Modelo Alert-Only: Nunca Bloqueia)
            if not strategy_state.active and can_search_strategy:
                # Captura o crupiê ativo na tela
                active_dealer = monitor.get_current_dealer()
                
                # SEMPRE busca estratégia, independente de warming_up ou turbulência
                signal = run_engine(
                    history=history_buffer.get_all(),
                    memory_agent=memory_agent,
                    base=numero,
                    dealer=active_dealer
                )
                if numero not in Settings.FORBIDDEN_NUMBERS and signal["strategy"]:
                    # LOG DE VALIDAÇÃO: Turbulência informativa não impede entrada
                    if has_turbulence and info.get("type") != "warming_up":
                        logger.info(
                            f"⚠️ Block ignorado por modo informativo de turbulência. Entrada para {numero} segue normalmente."
                        )

                    raw_strategy = signal["strategy"]
                    entry_targets = signal["entry_targets"]
                    protection_targets = signal["protection_targets"]
                    confidence = signal["confidence"]
                    reasoning = signal["reasoning"]

                    # Bloco IA (se disponível)
                    ai_block = ""
                    if signal.get("ai_used") and signal.get("ai_decision"):
                        ai_decision = signal["ai_decision"]
                        risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(
                            ai_decision.get("risk_level", "medium"), "🟡"
                        )
                        ai_block = (
                            f"🧠 IA ({ai_decision.get('confidence', 0)}% • {risk_emoji}):\n"
                            f"{ai_decision.get('reasoning', '')}\n\n"
                        )

                    time_now = datetime.now().strftime("%H:%M")
                    msg_completa = (
                        "🍀Entrada Confirmada🍀\n"
                        f"🕒 {time_now}\n"
                        f"📍 Número base: {numero}\n\n"
                        f"🎯 Entrada:\n{raw_strategy['entrada']}\n\n"
                        f"🛡️ Proteção:\n{raw_strategy.get('cobertura', '')}\n\n"
                        f"🧠 Leitura: {raw_strategy['leitura']}\n\n"
                        f"{ai_block}"
                        f"⏱️ Gestão:\nAté 3 proteções.\nSem insistência.\n\n"
                        f"💰 Gestão Sugerida: Ficha Base de {signal.get('kelly_stake', 1.0):.1f}% da Banca\n"
                        f"👤 Crupiê: {signal.get('dealer', 'Default')}"
                    )
                    logger.info(
                        f"✅ Estratégia confirmada para {numero}. Confiança: {confidence}%"
                    )
                    logger.info(f"Razão: {reasoning}")
                    # OTIMIZAÇÃO CRÍTICA DE LATÊNCIA: Envia ao HUD local imediatamente sem esperar o Telegram
                    send_signal_to_bridge(
                        number=numero,
                        strategy=raw_strategy["entrada"],
                        protection=raw_strategy.get("cobertura", ""),
                        leitura=raw_strategy["leitura"],
                        confidence=confidence,
                        kelly_stake=signal.get("kelly_stake", 1.0),
                        dealer=signal.get("dealer", "Default")
                    )
                    strategy_state.activate(
                        numero, numero, entry_targets, protection_targets
                    )

                    # Envia ao Telegram (independente, sem bloquear a atualização instantânea do HUD)
                    try:
                        bot.enviar_evento("SIGNAL", msg_completa)
                    except Exception as telegram_err:
                        logger.warning(
                            f"⚠️ Atraso ou erro no envio ao Telegram: {telegram_err}"
                        )
                else:
                    # LOG: Motivo exato de não enviar entrada
                    if numero in Settings.FORBIDDEN_NUMBERS:
                        logger.debug(
                            f"🚫 Número {numero} está na lista FORBIDDEN_NUMBERS. Sem estratégia."
                        )
                    else:
                        logger.debug(
                            f"📭 Sem estratégia registrada para o número {numero}."
                        )

            if time.time() - last_heartbeat > 60:
                logger.info("Heartbeat: Sistema ativo")
                last_heartbeat = time.time()

            time.sleep(0.5)

    except Exception as e:
        logger.error(f"Erro na execução da sessão: {e}", exc_info=True)
        return False  # Indica que a sessão caiu por erro
    finally:
        # Salva o perfil da sessão e perfis dos crupiês para aprendizado de longo prazo
        try:
            from ai.smart_brain import SmartBrain
            # Salva histórico das assinaturas de cada crupiê
            SmartBrain().save_croupier_profiles()
            
            total_signals = metrics.green_count + metrics.red_count
            win_rate = metrics.green_count / total_signals if total_signals > 0 else 0.80
            SmartBrain().rag.save_current_session_profile(
                session_id=str(session_id),
                history=history_buffer.get_all(),
                win_rate=win_rate
            )
        except Exception as rag_err:
            logger.warning(f"Erro ao salvar dados do SmartBrain na finalização: {rag_err}")

        db.end_session(session_id, metrics.numbers_detected, metrics.errors_count)
        monitor.stop()


def main():
    """Loop de resiliência (Auto-Restart)"""
    max_restarts = 10
    restart_count = 0

    while restart_count < max_restarts:
        try:
            success = run_bot()
            if success is False:
                restart_count += 1
                wait_time = min(60, 5 * restart_count)
                logger.warning(
                    f"Sessão encerrada com erro. Reiniciando em {wait_time}s ({restart_count}/{max_restarts})..."
                )
                time.sleep(wait_time)
            else:
                # Se run_bot retornar None ou True (saída limpa), podemos decidir se reiniciamos
                break
        except KeyboardInterrupt:
            logger.warning("Encerrando bot via teclado.")
            # Quando parado manualmente, tenta enviar o relatório final
            try:
                db = Database(str(Settings.DB_PATH))
                reporting = ReportingSystem(db)
                bot = TelegramBot(Settings.TELEGRAM_TOKEN, Settings.TELEGRAM_CHAT_ID)

                logger.info("Enviando relatório de encerramento...")
                relatorio = reporting.get_weekly_report(clean=True)
                bot.enviar(relatorio)
            except:
                pass
            break
        except Exception as fatal_e:
            logger.critical(f"Erro fatal não tratado: {fatal_e}")
            break


if __name__ == "__main__":
    main()
