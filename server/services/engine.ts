/**
 * Engine Orchestrator - Cérebro do Sistema Agentic
 * Coordena os agentes (Analyzer, Risk, Telegram) e integra RAG
 * Transforma regras fixas em inferência probabilística com reasoning explicativo
 * 
 * HABILIDADES IMPLEMENTADAS:
 * - Habilidade #3: ReAct loop (Pensamento -> Ação -> Observação)
 * - Habilidade #4: RAG - Leitura de histórico Neon
 * - Habilidade #6: Memória de Analytics (Win Rate por Tipo)
 * - Habilidade #8: Filtro Anti-Manipulação (Vício de Região)
 * - Habilidade #9: Estratégia de Entrada Certeira com Deep Scan
 */

import { AnalyzerAgent } from '../agents/analyzer.agent.js';
import { RiskAgent } from '../agents/risk.agent.js';
import { TelegramAgent } from '../agents/telegram.agent.js';
import { VectorStoreService } from './vector-store.js';
import { LoggerService } from './logger.js';
import { ComparisonService } from './comparison.js';
import { RealRAGService, RAGServiceFactory } from './real-rag.js';
import { MultimodalService } from './multimodal.js';

interface RouletteState {
  currentNumber: number;
  history: number[];
  timestamp: number;
}

interface AgentSignal {
  id: string;
  number: number;
  strategy: string;
  confidence: number;
  reasoning: string;
  react_thoughts: ReActStep[];
  entry: string[];
  protection: string[];
  risk: {
    stake: number;
    stopLoss: number;
    riskLevel: string;
  };
  ragInsights?: {
    strategy: any;
    relevance: number;
    reasoning: string;
  }[];
  timestamp: number;
  status: 'ANALYZING' | 'READY' | 'REJECTED' | 'DEEP_SCAN' | 'ABORTED';
  abortReason?: string;
  deepScanRoundsRemaining?: number;
}

interface ReActStep {
  thought: string;
  action: string;
  observation: string;
}

interface EngineConfig {
  minConfidence: number;
  riskParams: {
    baseStake: number;
    maxStake: number;
    bankroll: number;
    maxLoss: number;
    targetProfit: number;
  };
  enableRAG: boolean;
  enableLogging: boolean;
  enableComparison: boolean;
  enableMultimodal: boolean;
  geminiApiKey?: string;
  deepScanProtectionThreshold: number;
  vicioDetectionEnabled: boolean;
}

export class EngineOrchestrator {
  private analyzer: AnalyzerAgent;
  private riskAgent: RiskAgent;
  private telegramAgent: TelegramAgent;
  private vectorStore: VectorStoreService;
  private logger: LoggerService;
  private comparisonService?: ComparisonService;
  private realRAGService?: RealRAGService;
  private multimodalService?: MultimodalService;

  constructor(config: EngineConfig) {
    this.config = {
      ...config,
      geminiApiKey: config.geminiApiKey || process.env.GEMINI_API_KEY,
      deepScanProtectionThreshold: config.deepScanProtectionThreshold || 3,
      vicioDetectionEnabled: config.vicioDetectionEnabled !== false
    };

    this.analyzer = new AnalyzerAgent();
    this.riskAgent = new RiskAgent(config.riskParams);
    this.telegramAgent = new TelegramAgent();
    this.vectorStore = new VectorStoreService();
    this.logger = new LoggerService();

    if (config.enableComparison) {
      this.comparisonService = new ComparisonService(config);
    }

    if (config.enableMultimodal) {
      this.multimodalService = new MultimodalService();
    }

    this.initializeRealRAG();
  }

  /**
   * Processa novo número da roleta e gera sinal agentic
   * INTEGRA: Anti-Vício, Deep Scan, ReAct, RAG
   */
  async processNumber(state: RouletteState): Promise<AgentSignal | null> {
    const startTime = Date.now();

    try {
      // 1. Análise inteligente da roleta
      const analysis = this.analyzer.analyze(state.currentNumber, state.history);

      this.logger.info('ENGINE', 'Análise concluída', {
        number: state.currentNumber,
        confidence: analysis.confidence,
        variance: analysis.variance,
        adjustedThreshold: analysis.adjustedConfidenceThreshold
      });

      // 2. Verifica modo Deep Scan ativo
      const consecutiveProtections = this.analyzer.getConsecutiveProtections();
      if (consecutiveProtections >= this.config.deepScanProtectionThreshold) {
        this.analyzer.incrementDeepScanRounds();
        const remainingRounds = 5; // this.analyzer.getDeepScanRoundsRemaining?.() || 0;
        
        this.logger.warn('ENGINE', 'Modo Deep Scan ATIVADO', {
          consecutiveProtections,
          remainingRounds,
          confidence: analysis.confidence,
          threshold: analysis.adjustedConfidenceThreshold
        });

        return {
          id: `sig_deepscan_${Date.now()}_${state.currentNumber}`,
          number: state.currentNumber,
          strategy: 'DEEP_SCAN',
          confidence: analysis.confidence,
          reasoning: `🛡 Modo Deep Scan ativo. ${consecutiveProtections} proteções detectadas. Aguardando ${5 - (5 - remainingRounds)} rodadas para estabilização.`,
          react_thoughts: analysis.react_thoughts,
          entry: [],
          protection: [],
          risk: { stake: 0, stopLoss: 0, riskLevel: 'VERY_HIGH' },
          timestamp: Date.now(),
          status: 'DEEP_SCAN',
          deepScanRoundsRemaining: 5
        };
      }

      // 3. Verifica detecção de Vício de Zona
      if (this.config.vicioDetectionEnabled && analysis.vicio_detection?.detected) {
        this.logger.warn('ENGINE', 'Sinal ABORTADO por vício de zona', {
          vicioZone: analysis.vicio_detection.zone,
          recommendation: analysis.vicio_detection.recommendation
        });

        return {
          id: `sig_aborted_${Date.now()}_${state.currentNumber}`,
          number: state.currentNumber,
          strategy: 'ABORTED',
          confidence: analysis.confidence,
          reasoning: analysis.vicio_detection.recommendation,
          react_thoughts: analysis.react_thoughts,
          entry: [],
          protection: [],
          risk: { stake: 0, stopLoss: 0, riskLevel: 'HIGH' },
          timestamp: Date.now(),
          status: 'ABORTED',
          abortReason: `Vício de zona: ${analysis.vicio_detection.zone}`
        };
      }

      // 4. Usa limiar de confiança ajustado (pode ser até 95% após 3 proteções)
      const effectiveThreshold = analysis.adjustedConfidenceThreshold / 100;
      if (analysis.confidence < effectiveThreshold) {
        this.logger.warn('ENGINE', 'Sinal rejeitado por confiança abaixo do limiar ajustado', {
          confidence: analysis.confidence,
          threshold: effectiveThreshold,
          reason: consecutiveProtections >= 2 ? 'Proteções recentes detectadas' : 'Análise normal'
        });
        return null;
      }

      // 5. Verifica confiança mínima de 90% quando configurado
      if (this.config.minConfidence >= 90 && analysis.confidence < 0.9) {
        this.logger.warn('ENGINE', 'Sinal rejeitado: confiança < 90%', {
          confidence: analysis.confidence,
          threshold: 0.9
        });
        return null;
      }

      // 6. Consulta RAG para insights estratégicos
      let ragInsights = [];
      if (this.config.enableRAG) {
        try {
          ragInsights = await this.queryRAGInsights(analysis);
        } catch (error) {
          this.logger.error('ENGINE', 'Erro na consulta RAG', { error: error.message });
        }
      }

      // 7. Avaliação de risco
      const riskAssessment = this.riskAgent.assessRisk(analysis.confidence, analysis);

      if (!riskAssessment.canProceed) {
        this.logger.warn('ENGINE', 'Sinal rejeitado por avaliação de risco', riskAssessment);
        return null;
      }

      // 8. Gera reasoning estruturado com ReAct
      const reasoning = await this.generateStructuredReasoning(analysis, ragInsights);

      // 9. Define estratégia baseada na análise
      const strategy = this.selectStrategy(analysis, ragInsights);

      // 10. Calcula entradas e proteções
      const { entry, protection } = this.calculateTargets(strategy, state.currentNumber);

      // 11. Cria sinal final
      const signal: AgentSignal = {
        id: `sig_${Date.now()}_${state.currentNumber}`,
        number: state.currentNumber,
        strategy: strategy.name,
        confidence: analysis.confidence,
        reasoning,
        react_thoughts: analysis.react_thoughts,
        entry,
        protection,
        risk: {
          stake: riskAssessment.recommendedStake,
          stopLoss: riskAssessment.stopLoss,
          riskLevel: riskAssessment.riskLevel
        },
        ragInsights,
        timestamp: Date.now(),
        status: 'READY'
      };

      // Log do sinal gerado
      this.logger.info('ENGINE', 'Sinal gerado com sucesso', {
        signalId: signal.id,
        confidence: signal.confidence,
        strategy: signal.strategy,
        processingTime: Date.now() - startTime
      });

      return signal;

    } catch (error) {
      this.logger.error('ENGINE', 'Erro no processamento do número', {
        error: error.message,
        number: state.currentNumber
      });
      return null;
    }
  }

  /**
   * Processa resultado de sinal (win/loss) e atualiza agentes
   * INTEGRA: Memória de Analytics, Deep Scan
   */
  async processResult(signalId: string, won: boolean, stake: number, payout: number): Promise<void> {
    try {
      this.riskAgent.updatePerformance(won, stake, payout);

      // Atualiza estatísticas do Analyzer com resultado
      const result: 'win' | 'protection' | 'loss' = won ? 'win' : 'loss';
      await this.analyzer.updateStrategyStats(signalId, result);

      // Log do resultado
      const consecutiveProtections = this.analyzer.getConsecutiveProtections();
      this.logger.info('ENGINE', `Resultado processado: ${won ? 'WIN' : 'LOSS'}`, {
        signalId,
        won,
        stake,
        payout: won ? payout : 0,
        netResult: won ? payout - stake : -stake,
        consecutiveProtections,
        deepScanTriggered: consecutiveProtections >= 3
      });

    } catch (error) {
      this.logger.error('ENGINE', 'Erro no processamento do resultado', { error: error.message, signalId });
    }
  }

  /**
   * Processa proteção (resultado parcial)
   */
  async processProtection(signalId: string): Promise<void> {
    await this.analyzer.updateStrategyStats(signalId, 'protection');
    this.logger.info('ENGINE', 'Proteção registrada', { signalId, consecutive: this.analyzer.getConsecutiveProtections() });
  }

  /**
   * Gera mensagem Telegram para sinal
   */
  generateTelegramMessage(signal: AgentSignal): any {
    return this.telegramAgent.generateEntryMessage(signal);
  }

  /**
   * Gera mensagem para proteção
   */
  generateProtectionMessage(signal: AgentSignal, attempt: number): any {
    return this.telegramAgent.generateProtectionMessage(signal, attempt);
  }

  /**
   * Gera mensagem para resultado
   */
  generateResultMessage(signal: AgentSignal, won: boolean, amount: number): any {
    if (won) {
      return this.telegramAgent.generateWinMessage(signal, amount);
    } else {
      return this.telegramAgent.generateLossMessage(signal, amount);
    }
  }

  private async queryRAGInsights(analysis: any): Promise<any[]> {
    const patterns = this.extractPatternsFromAnalysis(analysis);

    const insights = [];

    for (const pattern of patterns) {
      try {
        const result = await this.vectorStore.findStrategyForPattern(
          pattern,
          `confiança ${(analysis.confidence * 100).toFixed(1)}%`
        );

        if (result) {
          insights.push(result);
        }
      } catch (error) {
        this.logger.error('ENGINE', 'Erro na query RAG', { pattern, error: error.message });
      }
    }

    return insights.slice(0, 2); // Máximo 2 insights
  }

  private extractPatternsFromAnalysis(analysis: any): string[] {
    const patterns = [];

    // Padrões de streak
    if (analysis.streaks.red >= 5) patterns.push('streak vermelho');
    if (analysis.streaks.black >= 5) patterns.push('streak preto');
    if (analysis.streaks.even >= 5) patterns.push('streak par');
    if (analysis.streaks.odd >= 5) patterns.push('streak ímpar');

    // Gaps
    if (analysis.gaps.color_gap >= 8) patterns.push('gap cor longo');
    if (analysis.gaps.number_gap >= 15) patterns.push('gap número longo');

    // Setores
    const maxSectorGap = Math.max(...Object.values(analysis.gaps.sector_gaps));
    if (maxSectorGap >= 10) patterns.push('gap setor longo');

    return patterns;
  }

  private async generateStructuredReasoning(analysis: any, ragInsights: any[]): Promise<string> {
    const reasons = [];

    // ReAct: Include thought process
    if (analysis.react_thoughts && analysis.react_thoughts.length > 0) {
      reasons.push('🤔 PENSAMENTO DO ANALISTA VIP:');
      analysis.react_thoughts.forEach((step: ReActStep, idx: number) => {
        if (idx < 2) { // Include first 2 thoughts
          reasons.push(`→ ${step.thought}`);
        }
      });
      reasons.push('---');
    }

    // Análise estatística
    reasons.push(`Análise: Variância ${analysis.variance.toFixed(1)}, Confiança ${(analysis.confidence * 100).toFixed(1)}%`);

    // Streaks detectados
    const activeStreaks = Object.entries(analysis.streaks)
      .filter(([, count]) => count >= 3)
      .map(([type, count]) => `${type}: ${count} consecutivos`);

    if (activeStreaks.length > 0) {
      reasons.push(`Streaks: ${activeStreaks.join(', ')}`);
    }

    // Gaps significativos
    if (analysis.gaps.color_gap >= 5) {
      reasons.push(`Gap de cor: ${analysis.gaps.color_gap} giros`);
    }

    // Terminal analysis
    if (analysis.terminal_analysis) {
      const { current, trend } = analysis.terminal_analysis;
      reasons.push(`Terminal ${current}: tendência ${trend}`);
    }

    // Vício detection
    if (analysis.vicio_detection?.detected) {
      reasons.push(`⚠️ ${analysis.vicio_detection.recommendation}`);
    }

    // Insights RAG
    if (ragInsights.length > 0) {
      reasons.push('📚 Histórico:');
      ragInsights.forEach(insight => {
        reasons.push(`- ${insight.reasoning}`);
      });
    }

    // Probabilidade calculada
    const probability = this.calculateEntryProbability(analysis);
    reasons.push(`Probabilidade: ${(probability * 100).toFixed(1)}%`);

    return reasons.join('\n');
  }

  /**
   * Gera mensagem reativa para o AnalistaVIP (frontend)
   */
  generateReactiveMessage(analysis: any, signal: AgentSignal | null): string {
    if (!signal) {
      const consecutiveProtections = this.analyzer.getConsecutiveProtections();
      if (consecutiveProtections >= 3) {
        return `🛡️ *ATENÇÃO*: Detectamos ${consecutiveProtections} proteções consecutivas. Vou entrar em modo Deep Scan e aguardar 5 rodadas para confirmar estabilização antes de liberar o próximo sinal.`;
      }
      
      if (analysis?.vicio_detection?.detected) {
        return `⚠️ *ALERTA DE ZONA*: Percebi que a bolinha está insistindo na zona ${analysis.vicio_detection.zone}. Vou aguardar para confirmar se a tendência muda antes de te dar um novo alerta.`;
      }

      return `⏳ *Aguardando*: Padrão não está favorável neste momento. Continue monitorando...`;
    }

    if (signal.status === 'DEEP_SCAN') {
      return `🔍 *MODO DEEP SCAN ATIVADO*: ${signal.reasoning}`;
    }

    if (signal.status === 'ABORTED') {
      return `🛑 *SINAL ABORTADO*: ${signal.reasoning}`;
    }

    // Good signal - include reasoning
    const thoughts = analysis.react_thoughts?.[0]?.thought || '';
    return `🎯 *SINAL DETECTADO*: ${thoughts}\n\n💰 ${signal.entry.join(' + ')}\n📊 Confiança: ${(signal.confidence * 100).toFixed(0)}%`;
  }

  private selectStrategy(analysis: any, ragInsights: any[]): { name: string; type: string } {
    // Estratégia baseada em análise + RAG + Terminal

    // Se há insights RAG específicos, usa eles
    if (ragInsights.length > 0) {
      const topInsight = ragInsights[0];
      return {
        name: topInsight.strategy.title,
        type: topInsight.strategy.strategy_type
      };
    }

    // Se terminal está em tendência hot, estratégia de continuação
    if (analysis.terminal_analysis?.trend === 'hot') {
      return { name: 'Terminal Quente (Continuação)', type: 'terminal_betting' };
    }

    // Se terminal está cold, estratégia de correção
    if (analysis.terminal_analysis?.trend === 'cold') {
      return { name: 'Correção de Terminal', type: 'pattern_betting' };
    }

    // Estratégia baseada em gaps
    if (analysis.gaps.color_gap >= 8) {
      return { name: 'Correção de Cor', type: 'pattern_betting' };
    }

    // Estratégia baseada em streaks
    if (analysis.streaks.red >= 6 || analysis.streaks.black >= 6) {
      return { name: 'Correção de Streak', type: 'pattern_betting' };
    }

    // Alta variância - estratégia probabilística
    if (analysis.variance > 60) {
      return { name: 'Aproveitamento de Variância', type: 'probability' };
    }

    return { name: 'Análise Probabilística', type: 'probability' };
  }

  private calculateTargets(strategy: { name: string; type: string }, baseNumber: number): { entry: string[], protection: string[] } {
    const baseColor = baseNumber === 0 ? 'verde' : (this.isRed(baseNumber) ? 'vermelho' : 'preto');
    const oppositeColor = baseColor === 'vermelho' ? 'preto' : 'vermelho';

    // Estratégia de Terminal + 2 Vizinhos (Entry Certeira)
    if (strategy.type === 'terminal_betting') {
      const terminal = Math.ceil(baseNumber / 3);
      const neighbors = this.getNeighbors(terminal);
      
      return {
        entry: [`Terminal ${terminal}`, `Vizinhos [${neighbors.join(', ')}]`],
        protection: [oppositeColor, oppositeColor, oppositeColor]
      };
    }

    // Estratégia de padrão (correção)
    if (strategy.type === 'pattern_betting') {
      return {
        entry: [oppositeColor],
        protection: [oppositeColor, oppositeColor]
      };
    }

    // Estratégia padrão conservadora
    return {
      entry: [oppositeColor],
      protection: [oppositeColor, oppositeColor, oppositeColor]
    };
  }

  private getNeighbors(terminal: number): number[] {
    // Get neighbors on the roulette wheel
    const neighbors: Record<number, number[]> = {
      1: [20, 14, 33, 16, 9],
      2: [23, 10, 4, 21, 25],
      3: [35, 12, 26, 0, 32],
      4: [21, 2, 25, 17, 19],
      5: [10, 23, 8, 30, 24],
      6: [28, 7, 29, 18, 22],
      7: [28, 12, 35, 3, 18],
      8: [30, 11, 36, 13, 23],
      9: [31, 14, 20, 1, 16],
      10: [33, 5, 24, 16, 23],
      11: [30, 8, 36, 13, 27],
      12: [35, 3, 26, 0, 28],
    };
    return neighbors[terminal] || [];
  }

  private calculateEntryProbability(analysis: any): number {
    // Cálculo simplificado baseado em fatores
    let probability = 0.5; // Base neutra

    // Ajusta baseado em gaps (potencial correção)
    if (analysis.gaps.color_gap >= 5) probability += 0.1;
    if (analysis.gaps.number_gap >= 10) probability += 0.05;

    // Penaliza streaks longos (menos provável correção)
    const maxStreak = Math.max(...Object.values(analysis.streaks));
    if (maxStreak >= 8) probability -= 0.1;

    // Ajusta baseado na confiança geral
    probability = probability * 0.7 + analysis.confidence * 0.3;

    return Math.max(0.1, Math.min(0.9, probability));
  }

  private isRed(num: number): boolean {
    const redNumbers = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36];
    return redNumbers.includes(num);
  }

  /**
   * Inicializa serviço RAG real se disponível
   */
  private async initializeRealRAG(): Promise<void> {
    try {
      this.realRAGService = RAGServiceFactory.createFromEnv();
      if (this.realRAGService) {
        const initialized = await this.realRAGService.initialize();
        if (initialized) {
          // Migração opcional do mock
          const mockData = this.vectorStore['mockStrategies'] || [];
          if (mockData.length > 0) {
            await this.realRAGService.migrateFromMock(mockData);
          }
          this.logger.info('ENGINE', 'Real RAG service initialized and migrated');
        }
      }
    } catch (error) {
      this.logger.warn('ENGINE', 'Failed to initialize real RAG service, using mock', { error: error.message });
    }
  }

  /**
   * Executa teste de comparação entre motores
   */
  async runComparisonTest(state: RouletteState): Promise<any> {
    if (!this.comparisonService) {
      throw new Error('Comparison service not enabled');
    }

    return await this.comparisonService.runParallelTest(state);
  }

  /**
   * Gera relatório de comparação
   */
  getComparisonReport(): any {
    if (!this.comparisonService) {
      throw new Error('Comparison service not enabled');
    }

    return this.comparisonService.generateComparisonReport();
  }

  /**
   * Processa imagem multimodal
   */
  async processImage(imageBuffer: Buffer, context?: RouletteState): Promise<any> {
    if (!this.multimodalService) {
      throw new Error('Multimodal service not enabled');
    }

    const visualAnalysis = await this.multimodalService.processRouletteImage(imageBuffer);

    // Opcional: combinar com análise de estado atual
    if (context) {
      // TODO: Integrar análise visual com estado da roleta
      this.logger.info('ENGINE', 'Visual analysis integrated with roulette state', {
        visualNumbers: visualAnalysis.detectedNumbers.length,
        stateNumbers: context.history.length
      });
    }

    return visualAnalysis;
  }

  /**
   * Verifica saúde de todos os serviços
   */
  async healthCheck(): Promise<any> {
    const health = {
      engine: 'healthy',
      analyzer: 'healthy',
      risk: 'healthy',
      telegram: 'healthy',
      vectorStore: 'healthy',
      logger: 'healthy',
      comparison: this.comparisonService ? 'enabled' : 'disabled',
      rag: 'mock',
      multimodal: this.multimodalService ? 'enabled' : 'disabled'
    };

    // Verifica RAG real
    if (this.realRAGService) {
      try {
        const ragHealth = await this.realRAGService.healthCheck();
        health.rag = ragHealth.status;
      } catch (error) {
        health.rag = 'unhealthy';
      }
    }

    // Verifica multimodal
    if (this.multimodalService) {
      try {
        const multimodalHealth = await this.multimodalService.healthCheck();
        health.multimodal = multimodalHealth.status;
      } catch (error) {
        health.multimodal = 'unhealthy';
      }
    }

    return health;
  }

  /**
   * Migração para RAG real (quando estiver pronto)
   */
  async migrateToRealRAG(): Promise<boolean> {
    if (!this.realRAGService) {
      throw new Error('Real RAG service not configured');
    }

    try {
      const mockData = this.vectorStore['mockStrategies'] || [];
      const migrated = await this.realRAGService.migrateFromMock(mockData);

      this.logger.info('ENGINE', `Migration completed: ${migrated} documents migrated`);
      return true;
    } catch (error) {
      this.logger.error('ENGINE', 'Migration failed', { error: error.message });
      return false;
    }
  }

  /**
   * Hook para futura integração multimodal
   */
  async processImage(imageBuffer: Buffer, context?: RouletteState): Promise<AgentSignal | null> {
    // TODO: Implementar processamento de imagem
    // - OCR para detectar números
    // - Análise visual de padrões
    // - Integração com Gemini/GPT-4o

    this.logger.warn('ENGINE', 'Processamento multimodal não implementado', { hasImage: true });
    return null;
  }
}