/**
 * Telegram Agent - Copywriting persuasivo para sinais enviados
 * Responsável por gerar mensagens atrativas e pedagógicas para o usuário,
 * explicando o raciocínio de forma clara e motivadora.
 */

interface SignalData {
  number: number;
  strategy: string;
  confidence: number;
  reasoning: string;
  entry: string[];
  protection: string[];
  risk: {
    stake: number;
    stopLoss: number;
    riskLevel: string;
  };
}

interface TelegramMessage {
  text: string;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  includeEmoji: boolean;
}

export class TelegramAgent {
  private personality = {
    enthusiastic: "🚀 ENTRADA CONFIRMADA 🚀",
    cautious: "⚠️ OPORTUNIDADE COM CAUTELA ⚠️",
    conservative: "🎯 ENTRADA CONSERVADORA 🎯"
  };

  /**
   * Gera mensagem persuasiva para sinal de entrada
   */
  generateEntryMessage(signal: SignalData): TelegramMessage {
    const personality = this.selectPersonality(signal.confidence);

    const header = this.generateHeader(signal, personality);
    const analysis = this.generateAnalysis(signal);
    const recommendation = this.generateRecommendation(signal);
    const riskWarning = this.generateRiskWarning(signal);
    const motivation = this.generateMotivation(signal);

    const fullText = [
      header,
      '',
      analysis,
      '',
      recommendation,
      '',
      riskWarning,
      '',
      motivation
    ].join('\n');

    return {
      text: fullText,
      priority: this.getPriority(signal),
      includeEmoji: true
    };
  }

  /**
   * Gera mensagem para proteção/gale
   */
  generateProtectionMessage(signal: SignalData, attempt: number): TelegramMessage {
    const text = [
      `🛡️ PROTEÇÃO ${attempt}/3 ATIVADA`,
      '',
      `Mantendo a estratégia após ${signal.number}`,
      `Confiança mantida em ${(signal.confidence * 100).toFixed(1)}%`,
      '',
      '🎲 Próxima entrada:',
      ...signal.entry.map(target => `• ${target}`),
      '',
      '💪 Disciplina é fundamental. Uma proteção bem calculada vale mais que 10 entradas precipitadas.'
    ].join('\n');

    return {
      text,
      priority: 'MEDIUM',
      includeEmoji: true
    };
  }

  /**
   * Gera mensagem para resultado WIN
   */
  generateWinMessage(signal: SignalData, profit: number): TelegramMessage {
    const text = [
      `💰 WIN CONFIRMADO! +R$ ${profit.toFixed(2)}`,
      '',
      `✅ ${signal.number} entrou exatamente como previsto!`,
      '',
      `📊 Estatísticas atualizadas:`,
      `🎯 Precisão: ${(signal.confidence * 100).toFixed(1)}%`,
      `💼 Lucro: R$ ${profit.toFixed(2)}`,
      '',
      '🌟 Cada vitória é uma lição aprendida. Continue assim!'
    ].join('\n');

    return {
      text,
      priority: 'HIGH',
      includeEmoji: true
    };
  }

  /**
   * Gera mensagem para resultado LOSS
   */
  generateLossMessage(signal: SignalData, loss: number): TelegramMessage {
    const text = [
      `📉 LOSS REGISTRADO -R$ ${loss.toFixed(2)}`,
      '',
      `❌ ${signal.number} não cooperou desta vez`,
      '',
      `📚 Lição aprendida:`,
      `• Mercado é imprevisível`,
      `• Gestão de risco protegeu o bankroll`,
      `• Stop Loss ativado corretamente`,
      '',
      '🔄 Preparando próxima oportunidade com ainda mais inteligência.'
    ].join('\n');

    return {
      text,
      priority: 'MEDIUM',
      includeEmoji: false
    };
  }

  private selectPersonality(confidence: number): string {
    if (confidence >= 0.85) return this.personality.enthusiastic;
    if (confidence >= 0.7) return this.personality.conservative;
    return this.personality.cautious;
  }

  private generateHeader(signal: SignalData, personality: string): string {
    const time = new Date().toLocaleTimeString('pt-BR', {
      hour: '2-digit',
      minute: '2-digit'
    });

    return [
      personality,
      `🕒 ${time}`,
      `🎲 Base: ${signal.number}`,
      `🎯 Confiança: ${(signal.confidence * 100).toFixed(1)}%`
    ].join('\n');
  }

  private generateAnalysis(signal: SignalData): string {
    // Quebra o reasoning em pontos principais
    const reasoningPoints = this.parseReasoning(signal.reasoning);

    return [
      '🔍 ANÁLISE INTELIGENTE:',
      ...reasoningPoints.map(point => `• ${point}`)
    ].join('\n');
  }

  private generateRecommendation(signal: SignalData): string {
    return [
      '🎯 RECOMENDAÇÃO:',
      `💰 Stake: R$ ${signal.risk.stake.toFixed(2)}`,
      `🎲 Entrada:`,
      ...signal.entry.map(target => `   • ${target}`),
      `🛡️ Proteção:`,
      ...signal.protection.map(target => `   • ${target}`),
      '',
      '⏱️ Gestão: Até 3 proteções',
      '🚫 Sem insistência após stop loss'
    ].join('\n');
  }

  private generateRiskWarning(signal: SignalData): string {
    const warnings = [];

    if (signal.risk.riskLevel === 'HIGH') {
      warnings.push('⚠️ RISCO ELEVADO - Considere reduzir stake');
    }

    if (signal.risk.riskLevel === 'VERY_HIGH') {
      warnings.push('🚨 RISCO MUITO ALTO - Avalie se deve prosseguir');
    }

    warnings.push(`🛑 Stop Loss: R$ ${signal.risk.stopLoss.toFixed(2)}`);

    return [
      '⚠️ GESTÃO DE RISCO:',
      ...warnings
    ].join('\n');
  }

  private generateMotivation(signal: SignalData): string {
    const motivations = [
      '🌟 A paciência do caçador é recompensada pelo tigre.',
      '🎪 No circo da fortuna, o equilíbrio é a chave mestra.',
      '🏆 Cada decisão é um passo rumo à maestria.',
      '💎 Diamantes são carvão que suportou pressão. Seja o diamante.',
      '🎭 A roleta dança ao ritmo da probabilidade, nós dançamos ao ritmo da disciplina.'
    ];

    const randomMotivation = motivations[Math.floor(Math.random() * motivations.length)];

    return `💭 "${randomMotivation}"`;
  }

  private parseReasoning(reasoning: string): string[] {
    // Quebra o reasoning do analyzer agent em pontos
    const sentences = reasoning.split(/[.!?]+/).filter(s => s.trim());

    // Pega os 3 pontos mais relevantes
    return sentences.slice(0, 3).map(s => s.trim());
  }

  private getPriority(signal: SignalData): 'HIGH' | 'MEDIUM' | 'LOW' {
    if (signal.confidence >= 0.85) return 'HIGH';
    if (signal.confidence >= 0.7) return 'MEDIUM';
    return 'LOW';
  }

  /**
   * Gera resumo diário de performance
   */
  generateDailySummary(stats: any): TelegramMessage {
    const text = [
      '📊 RESUMO DO DIA',
      '',
      `🎯 Total de sinais: ${stats.totalSignals}`,
      `💰 Lucro/Prejuízo: R$ ${stats.totalPnL.toFixed(2)}`,
      `📈 Taxa de acerto: ${(stats.winRate * 100).toFixed(1)}%`,
      `🔥 Melhor sequência: ${stats.bestStreak} vitórias`,
      '',
      stats.totalPnL > 0
        ? '🌟 Dia positivo! Continue a disciplina.'
        : '📚 Dia de aprendizado. Amanhã é uma nova oportunidade.'
    ].join('\n');

    return {
      text,
      priority: 'HIGH',
      includeEmoji: true
    };
  }
}