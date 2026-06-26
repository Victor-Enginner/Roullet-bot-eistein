/**
 * Comparison Service - Compara motores Python e Agentic
 * Permite teste em paralelo e métricas de comparação
 */

import { EngineOrchestrator } from './engine.js';
import { LoggerService } from './logger.js';

interface ComparisonResult {
  number: number;
  pythonEngine: {
    signal: any;
    confidence: number;
    strategy: string;
    responseTime: number;
    reasoning?: string;
  };
  agenticEngine: {
    signal: any;
    confidence: number;
    strategy: string;
    responseTime: number;
    reasoning: string;
  };
  comparison: {
    accuracy: 'AGENTIC_BETTER' | 'PYTHON_BETTER' | 'TIE' | 'NO_SIGNALS';
    responseTimeDiff: number;
    explainabilityScore: 'AGENTIC_BETTER' | 'PYTHON_BETTER' | 'TIE';
    ragInsights: number;
  };
  timestamp: number;
}

interface RouletteState {
  currentNumber: number;
  history: number[];
  timestamp: number;
}

export class ComparisonService {
  private agenticEngine: EngineOrchestrator;
  private logger: LoggerService;
  private comparisonHistory: ComparisonResult[] = [];

  constructor(agenticConfig: any) {
    this.agenticEngine = new EngineOrchestrator(agenticConfig);
    this.logger = new LoggerService();
  }

  /**
   * Executa teste paralelo entre motores Python e Agentic
   */
  async runParallelTest(state: RouletteState): Promise<ComparisonResult> {
    const startTime = Date.now();

    // Simula resultado do motor Python (baseado na análise do código existente)
    const pythonResult = await this.simulatePythonEngine(state);
    const pythonTime = Date.now() - startTime;

    // Executa motor agentic
    const agenticStart = Date.now();
    const agenticSignal = await this.agenticEngine.processNumber(state);
    const agenticTime = Date.now() - agenticStart;

    // Cria resultado da comparação
    const result: ComparisonResult = {
      number: state.currentNumber,
      pythonEngine: {
        signal: pythonResult.signal,
        confidence: pythonResult.confidence,
        strategy: pythonResult.strategy,
        responseTime: pythonTime,
        reasoning: pythonResult.reasoning
      },
      agenticEngine: {
        signal: agenticSignal,
        confidence: agenticSignal?.confidence || 0,
        strategy: agenticSignal?.strategy || 'NONE',
        responseTime: agenticTime,
        reasoning: agenticSignal?.reasoning || 'Nenhum sinal gerado'
      },
      comparison: {
        accuracy: this.compareAccuracy(pythonResult, agenticSignal),
        responseTimeDiff: agenticTime - pythonTime,
        explainabilityScore: this.compareExplainability(pythonResult, agenticSignal),
        ragInsights: agenticSignal?.ragInsights?.length || 0
      },
      timestamp: Date.now()
    };

    // Salva no histórico
    this.comparisonHistory.push(result);

    // Log da comparação
    this.logger.info('COMPARISON', 'Teste paralelo concluído', {
      number: state.currentNumber,
      pythonConfidence: result.pythonEngine.confidence,
      agenticConfidence: result.agenticEngine.confidence,
      accuracy: result.comparison.accuracy,
      responseTimeDiff: result.comparison.responseTimeDiff,
      explainability: result.comparison.explainabilityScore
    });

    return result;
  }

  /**
   * Simula o comportamento do motor Python atual
   */
  private async simulatePythonEngine(state: RouletteState): Promise<any> {
    // Simulação baseada na análise do main_playtech.py e signals/engine.py

    const history = state.history.slice(-50); // Últimos 50 números
    const currentNumber = state.currentNumber;

    // Lógica simplificada do motor Python
    const streaks = this.calculateStreaks(history, currentNumber);
    const confidence = this.calculatePythonConfidence(streaks);

    if (confidence >= 0.7) {
      return {
        signal: {
          number: currentNumber,
          strategy: 'Pattern Strategy',
          confidence,
          entry: ['opposite_color'],
          protection: ['opposite_color', 'opposite_color']
        },
        confidence,
        strategy: 'Pattern Strategy',
        reasoning: `Motor Python: Confiança ${confidence.toFixed(2)} baseada em streaks.`
      };
    }

    return {
      signal: null,
      confidence: 0,
      strategy: 'NONE',
      reasoning: 'Motor Python: Sem sinal gerado'
    };
  }

  private calculateStreaks(history: number[], currentNumber: number): any {
    let red = 0, black = 0, even = 0, odd = 0;

    for (let i = history.length - 1; i >= 0; i--) {
      const num = history[i];
      if (this.isRed(num)) red++;
      else if (num !== 0) black++;

      if (num % 2 === 0) even++;
      else odd++;
    }

    return { red, black, even, odd };
  }

  private calculatePythonConfidence(streaks: any): number {
    // Simulação da lógica Python simplificada
    const maxStreak = Math.max(...Object.values(streaks));
    let confidence = 0.5;

    if (maxStreak >= 5) confidence += 0.2;
    if (maxStreak >= 8) confidence += 0.3;

    return Math.min(0.95, confidence);
  }

  private isRed(num: number): boolean {
    const redNumbers = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36];
    return redNumbers.includes(num);
  }

  private compareAccuracy(python: any, agentic: any): 'AGENTIC_BETTER' | 'PYTHON_BETTER' | 'TIE' | 'NO_SIGNALS' {
    const pythonHasSignal = python.signal !== null;
    const agenticHasSignal = agentic !== null;

    if (!pythonHasSignal && !agenticHasSignal) return 'NO_SIGNALS';
    if (!pythonHasSignal && agenticHasSignal) return 'AGENTIC_BETTER';
    if (pythonHasSignal && !agenticHasSignal) return 'PYTHON_BETTER';

    // Ambos têm sinais - compara confiança
    const diff = agentic.confidence - python.confidence;
    if (Math.abs(diff) < 0.1) return 'TIE';
    return diff > 0 ? 'AGENTIC_BETTER' : 'PYTHON_BETTER';
  }

  private compareExplainability(python: any, agentic: any): 'AGENTIC_BETTER' | 'PYTHON_BETTER' | 'TIE' {
    const pythonReasoning = python.reasoning || '';
    const agenticReasoning = agentic?.reasoning || '';

    const pythonScore = this.scoreExplainability(pythonReasoning);
    const agenticScore = this.scoreExplainability(agenticReasoning);

    if (agenticScore > pythonScore + 2) return 'AGENTIC_BETTER';
    if (pythonScore > agenticScore + 2) return 'PYTHON_BETTER';
    return 'TIE';
  }

  private scoreExplainability(reasoning: string): number {
    let score = 0;

    // Comprimento do reasoning
    if (reasoning.length > 100) score += 2;
    else if (reasoning.length > 50) score += 1;

    // Estrutura (pontos numerados)
    if (reasoning.includes('1.') || reasoning.includes('•')) score += 1;

    // Menciona probabilidade/confiança
    if (reasoning.toLowerCase().includes('probabilidade') ||
        reasoning.toLowerCase().includes('confiança')) score += 1;

    // Menciona estratégia
    if (reasoning.toLowerCase().includes('estratégia')) score += 1;

    return score;
  }

  /**
   * Gera relatório de comparação
   */
  generateComparisonReport(): any {
    if (this.comparisonHistory.length === 0) {
      return { message: 'Nenhum teste executado ainda' };
    }

    const total = this.comparisonHistory.length;
    const agenticBetter = this.comparisonHistory.filter(c => c.comparison.accuracy === 'AGENTIC_BETTER').length;
    const pythonBetter = this.comparisonHistory.filter(c => c.comparison.accuracy === 'PYTHON_BETTER').length;
    const ties = this.comparisonHistory.filter(c => c.comparison.accuracy === 'TIE').length;

    const avgResponseTimeDiff = this.comparisonHistory.reduce((acc, c) => acc + c.comparison.responseTimeDiff, 0) / total;
    const avgRagInsights = this.comparisonHistory.reduce((acc, c) => acc + c.comparison.ragInsights, 0) / total;

    return {
      totalTests: total,
      accuracyComparison: {
        agenticBetter,
        pythonBetter,
        ties,
        agenticWinRate: (agenticBetter / (agenticBetter + pythonBetter)) * 100
      },
      performanceComparison: {
        avgResponseTimeDiff, // Diferença positiva = agentic mais lento
        avgRagInsights
      },
      explainabilityComparison: {
        agenticBetter: this.comparisonHistory.filter(c => c.comparison.explainabilityScore === 'AGENTIC_BETTER').length,
        pythonBetter: this.comparisonHistory.filter(c => c.comparison.explainabilityScore === 'PYTHON_BETTER').length,
        ties: this.comparisonHistory.filter(c => c.comparison.explainabilityScore === 'TIE').length
      },
      recentTests: this.comparisonHistory.slice(-5)
    };
  }

  /**
   * Limpa histórico de comparações
   */
  clearHistory(): void {
    this.comparisonHistory = [];
    this.logger.info('COMPARISON', 'Histórico de comparações limpo');
  }
}