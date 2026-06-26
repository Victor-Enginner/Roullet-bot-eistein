from server.agents.analyzer import analyze_recent
from server.agents.strategy import pick_strategy
from server.agents.memory import MemoryAgent
from engine.parser import parse_strategy_targets, parse_protection_targets

# Integração opcional com IA local (Ollama)
try:
    from ai.ollama_agent import get_analyst, AIResponse
    AI_ENABLED = True
except Exception:
    AI_ENABLED = False


def calculate_confidence(analysis: dict, stats: dict) -> int:
    """
    Calcula confiança baseada na análise e estatísticas.
    """
    score = 50

    hot_numbers = [num for num, _ in analysis["hot_numbers"]]
    if stats.get("base") in hot_numbers:
        score += 15

    direct_green = stats.get("directGreen", 0)
    loss = stats.get("loss", 0)
    if direct_green > loss:
        score += 20
    if loss > 2:
        score -= 25

    return max(0, min(100, score))


def generate_reasoning(analysis: dict, strategy: dict, stats: dict) -> str:
    """
    Gera explicação para a decisão.
    """
    leitura = strategy.get("leitura", "")
    direct_green = stats.get("directGreen", 0)
    loss = stats.get("loss", 0)

    return f"""
Leitura: {leitura}

Base com histórico de {direct_green} greens diretos
e {loss} losses.

Terminal dominante detectado.
Padrão consistente nos últimos 100 giros.
""".strip()


def run_engine(
    history: list[int],
    memory_agent: MemoryAgent,
    base: int,
    use_ai: bool = True,
    dealer: str = "Default",
) -> dict:
    """
    Executa o engine combinando análise, estratégia e memória.

    Se use_ai=True e Ollama estiver disponível, consulta o agente de IA
    para validar/ajustar a estratégia. Em caso de falha da IA, usa a
    lógica clássica como fallback.
    """
    analysis = analyze_recent(history)
    strategy = pick_strategy(base, history)
    stats = memory_agent.get_stats(base)

    # Inicialização do SmartBrain (Evoluções de IA)
    try:
        from ai.smart_brain import SmartBrain
        smart_brain = SmartBrain()
        # Sincroniza histórico para a assinatura geométrica do crupiê específico
        if history:
            tracker = smart_brain.get_croupier_tracker(dealer)
            tracker.history = []
            for num in history[-15:]:
                tracker.add_spin(num)
        
        # Pega as calibrações de peso (Q-Learning e RAG de Sessão)
        q_weight = smart_brain.q_learning.get_weight(base)
        rag_winrate = smart_brain.rag.query_similar_session_winrate(history)
    except Exception as sb_err:
        import logging
        logging.getLogger("server.services.engine").warning(f"⚠️ Erro ao inicializar SmartBrain: {sb_err}")
        q_weight = 1.0
        rag_winrate = 0.80
        smart_brain = None

    # Parse targets (lógica clássica)
    entry_targets = parse_strategy_targets(strategy.get("entrada", ""))
    protection_targets = parse_protection_targets(strategy.get("cobertura", ""))

    # Defaults (lógica clássica)
    confidence = calculate_confidence(analysis, stats)
    reasoning = generate_reasoning(analysis, strategy, stats)
    ai_used = False
    ai_decision = None
    risk_level = "unknown"

    # Consulta IA (opcional)
    if use_ai and AI_ENABLED:
        try:
            analyst = get_analyst()
            ai_decision = analyst.analyze(
                history=history,
                base=base,
                strategy=strategy,
                stats=stats,
                analysis=analysis,
                current_number=history[-1] if history else base,
            )
            if ai_decision is not None:
                ai_used = True
                risk_level = ai_decision.risk_level

                # Se a IA autorizou a entrada e detectou assinatura física consistente, sugere alvos adicionais
                if ai_decision.should_enter and smart_brain and history:
                    tracker = smart_brain.get_croupier_tracker(dealer)
                    predicted_sector = tracker.predict_target_sector(history[-1])
                    if predicted_sector:
                        # Adiciona vizinhos geométricos do cilindro aos alvos alternativos
                        ai_decision.alternative_targets = list(set(ai_decision.alternative_targets + predicted_sector))

                # IA como consultora: mistura inteligente
                # Se IA diz should_enter=False com confiança alta, anula entrada
                if not ai_decision.should_enter and ai_decision.confidence >= 70:
                    confidence = ai_decision.confidence
                    reasoning = f"🧠 IA contraindicou: {ai_decision.reasoning}"
                    entry_targets = []  # zera entrada (caller deve checar)
                else:
                    # Média ponderada: 40% clássica + 60% IA
                    confidence = int(confidence * 0.4 + ai_decision.confidence * 0.6)
                    # Aplica calibradores SmartBrain (Q-Learning e RAG de Sessão)
                    confidence = int(confidence * q_weight * (rag_winrate / 0.80))
                    confidence = max(0, min(100, confidence))
                    reasoning = ai_decision.reasoning or reasoning

                # Se IA sugeriu alvos alternativos e entrada clássica está vazia
                if not entry_targets and ai_decision.alternative_targets:
                    entry_targets = ai_decision.alternative_targets

        except Exception as e:
            # Fallback silencioso - registra o erro para diagnóstico
            import logging
            logging.getLogger("server.services.engine").warning(f"⚠️ Erro ao executar IA no engine: {e}", exc_info=True)

    # Calibra Kelly Stake
    kelly_stake = 1.0
    if smart_brain:
        kelly_stake = smart_brain.calculate_kelly_fraction(confidence)

    return {
        "base": base,
        "strategy": strategy,
        "confidence": confidence,
        "reasoning": reasoning,
        "entry_targets": entry_targets,
        "protection_targets": protection_targets,
        "ai_used": ai_used,
        "ai_decision": ai_decision.to_dict() if ai_decision else None,
        "risk_level": risk_level,
        "kelly_stake": kelly_stake,
        "dealer": dealer,
    }
