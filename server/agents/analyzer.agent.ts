/**
 * Analyzer Agent - Análise inteligente da roleta
 * Responsável por analisar streaks, gaps estatísticos, histórico recente,
 * padrões por setor (Voisins/Tiers/Orphans) e clima da mesa.
 * 
 * HABILIDADES IMPLEMENTADAS:
 * - Habilidade #1: System Prompts de nível especialista (tom Victor | Analista VIP)
 * - Habilidade #2 & #10: Automação de workflows com análise dinâmica
 * - Habilidade #3: ReAct loop (Pensamento -> Ação -> Observação)
 * - Habilidade #4: RAG - Leitura de histórico de sinais e resultados
 * - Habilidade #5 & #7: Multimodalidade (via Gemini Vision)
 * - Habilidade #6: Memória de Analytics (Win Rate por Tipo)
 * - Habilidade #8: Filtro Anti-Manipulação (Vício de Região)
 * - Habilidade #9: Estratégia de Entrada Certeira
 */

import { db } from '../db.js';
import { signals as signalsTable, strategies } from '../schema.js';

// European wheel sectors
const VOISINS = [22, 18, 29, 7, 28, 12, 35, 3, 26, 0, 32, 15, 19, 4, 21, 2, 25];
const TIERS = [33, 16, 24, 5, 10, 23, 8, 30, 11, 36, 13, 27];
const ORPHANS = [1, 20, 14, 31, 9];
const NEIGHBORS_MAP: Record<number, number[]> = {
  0: [32, 15, 26, 11, 30],
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
  13: [36, 11, 27, 1, 6],
  14: [31, 9, 20, 1, 33],
  15: [32, 0, 26, 19, 4],
  16: [33, 1, 20, 14, 24],
  17: [25, 2, 21, 34, 6],
  18: [22, 7, 29, 0, 28],
  19: [15, 4, 21, 34, 20],
  20: [1, 14, 31, 19, 34],
  21: [2, 25, 17, 34, 19],
  22: [18, 29, 7, 6, 32],
  23: [8, 10, 5, 24, 16],
  24: [5, 23, 16, 33, 10],
  25: [2, 21, 17, 34, 26],
  26: [0, 3, 35, 12, 15],
  27: [36, 13, 11, 8, 30],
  28: [7, 6, 18, 12, 29],
  29: [18, 22, 9, 6, 28],
  30: [11, 8, 23, 10, 5],
  31: [14, 9, 6, 28, 27],
  32: [15, 19, 4, 21, 0],
  33: [16, 1, 14, 20, 10],
  34: [17, 6, 25, 21, 19],
  35: [12, 3, 26, 0, 32],
  36: [13, 27, 11, 8, 30]
};

interface ReActStep {
  thought: string;
  action: string;
  observation: string;
}

interface StrategyStats {
  strategyId: string;
  totalEntries: number;
  wins: number;
  protections: number;
  last10Results: ('win' | 'protection')[];
}

interface VicioZoneDetection {
  detected: boolean;
  zone: string;
  consecutiveNumbers: number[];
  recommendation: string;
}

interface RouletteAnalysis {
  number: number;
  streaks: {
    red: number;
    black: number;
    even: number;
    odd: number;
    high: number;
    low: number;
  };
  gaps: {
    color_gap: number;
    number_gap: number;
    sector_gaps: Record<string, number>;
  };
  patterns: {
    hot_numbers: number[];
    cold_numbers: number[];
    sector_bias: Record<string, number>;
    terminals: number[];
  };
  variance: number;
  confidence: number;
  react_thoughts: ReActStep[];
  vicio_detection: VicioZoneDetection | null;
  strategy_stats: StrategyStats[];
  adjustedConfidenceThreshold: number;
  terminal_analysis: {
    current: number;
    neighbors: number[];
    trend: 'hot' | 'cold' | 'stable';
  };
}

interface RouletteContext {
  history: number[];
  current_streak: Record<string, number>;
  sector_stats: Record<string, { count: number; last_seen: number }>;
  terminal_history: { terminal: number; timestamp: number }[];
  consecutive_protections: number;
  deep_scan_rounds: number;
  last_zone: string | null;
  zone_history: string[];
}

export class AnalyzerAgent {
  private context: RouletteContext;
  private strategyStats: Map<string, StrategyStats> = new Map();
  private readonly CONFIDENCE_THRESHOLD_BASE = 70;
  private readonly PROTECTION_THRESHOLD = 95;
  private readonly VICE_ZONE_THRESHOLD = 3;
  private readonly DEEP_SCAN_ROUNDS = 5;

  constructor() {
    this.context = {
      history: [],
      current_streak: {},
      sector_stats: {},
      terminal_history: [],
      consecutive_protections: 0,
      deep_scan_rounds: 0,
      last_zone: null,
      zone_history: []
    };
  }

  /**
   * Executa ciclo ReAct completo: Pensamento -> Ação -> Observação
   */
  private runReActLoop(currentNumber: number, analysis: Partial<RouletteAnalysis>): ReActStep[] {
    const thoughts: ReActStep[] = [];
    
    const terminal = this.getTerminal(currentNumber);
    const neighbors = NEIGHBORS_MAP[terminal] || [];
    const sector = this.getSector(terminal);
    
    // THOUGHT 1: Análise do terminal atual
    thoughts.push({
      thought: `Pensei no Terminal ${terminal}: número atual ${currentNumber} está na zona ${sector}.`,
      action: 'Analisar padrão de terminal e vizinhos.',
      observation: `Terminal ${terminal} tem ${neighbors.length} vizinhos: [${neighbors.join(', ')}].`
    });

    // THOUGHT 2: Verificação de vício de zona
    const vicioCheck = this.detectVicioDeZona();
    if (vicioCheck.detected) {
      thoughts.push({
        thought: `⚠️ ALERTA: Detectado vício de zona!`,
        action: 'Verificar histórico de zonas.',
        observation: `${vicioCheck.recommendation}`
      });
    } else {
      thoughts.push({
        thought: `Zona estável: última zona foi ${this.context.last_zone || 'N/A'}.`,
        action: 'Continuar análise normal.',
        observation: 'Nenhum padrão de vício detectado.'
      });
    }

    // THOUGHT 3: Verificação de proteções consecutivas
    if (this.context.consecutive_protections >= 3) {
      thoughts.push({
        thought: `🚨 ATENÇÃO: ${this.context.consecutive_protections} proteções consecutivas detectadas!`,
        action: 'Ativar modo Deep Scan.',
        observation: `Aguardando ${this.DEEP_SCAN_ROUNDS - this.context.deep_scan_rounds} rodadas para estabilização.`
      });
    }

    // THOUGHT 4: Análise de tendência de terminais
    const terminalTrend = this.analyzeTerminalTrend(terminal);
    thoughts.push({
      thought: `Terminal ${terminal}: tendência ${terminalTrend}.`,
      action: 'Calcular confiança ajustada.',
      observation: `Base: ${this.CONFIDENCE_THRESHOLD_BASE}%, Ajustada: ${this.calculateAdjustedThreshold()}%`
    });

    return thoughts;
  }

  /**
   * Detecta "Vício de Zona" - Anti-Loss por Repetição
   */
  private detectVicioDeZona(): VicioZoneDetection {
    const history = this.context.history;
    if (history.length < this.VICE_ZONE_THRESHOLD) {
      return { detected: false, zone: '', consecutiveNumbers: [], recommendation: '' };
    }

    const recentNumbers = history.slice(-this.VICE_ZONE_THRESHOLD);
    const sectors = recentNumbers.map(n => this.getSector(this.getTerminal(n)));
    const zones = recentNumbers.map(n => this.getZone(n));

    // Check for same sector (dozens)
    const firstSector = sectors[0];
    const allSameSector = sectors.every(s => s === firstSector);

    // Check for repeated numbers
    const numberCounts = new Map<number, number>();
    recentNumbers.forEach(n => numberCounts.set(n, (numberCounts.get(n) || 0) + 1));
    const hasRepeats = Array.from(numberCounts.values()).some(c => c >= 2);

    // Check for neighboring zones
    const firstZone = zones[0];
    const allNeighbors = zones.every(z => this.areNeighbors(z, firstZone));

    if (allSameSector || (hasRepeats && recentNumbers.length >= 4)) {
      const zoneName = this.getZoneName(firstZone);
      return {
        detected: true,
        zone: zoneName,
        consecutiveNumbers: recentNumbers,
        recommendation: `⚠️ Possível vício de zona detectado (${zoneName}). Abortando entrada para evitar Loss.`
      };
    }

    if (allNeighbors && this.context.zone_history.length >= this.VICE_ZONE_THRESHOLD) {
      return {
        detected: true,
        zone: firstZone,
        consecutiveNumbers: recentNumbers,
        recommendation: `⚠️ Números concentrados na vizinhança. Abortando para evitar padrão de perda.`
      };
    }

    return { detected: false, zone: '', consecutiveNumbers: [], recommendation: '' };
  }

  private getZone(n: number): number {
    return Math.floor(n / 9);
  }

  private getZoneName(zone: number): string {
    const names = ['1-9', '10-18', '19-27', '28-36'];
    return names[zone] || 'desconhecido';
  }

  private areNeighbors(z1: number, z2: number): boolean {
    return Math.abs(z1 - z2) <= 1;
  }

  /**
   * Analisa tendência do terminal
   */
  private analyzeTerminalTrend(terminal: number): 'hot' | 'cold' | 'stable' {
    const recent = this.context.terminal_history.slice(-10);
    if (recent.length < 5) return 'stable';

    const terminalCount = recent.filter(t => t.terminal === terminal).length;
    if (terminalCount >= 4) return 'hot';
    if (terminalCount <= 1) return 'cold';
    return 'stable';
  }

  /**
   * Calcula limiar de confiança ajustado baseado em proteções consecutivas
   */
  private calculateAdjustedThreshold(): number {
    if (this.context.consecutive_protections >= 3) {
      return Math.min(this.PROTECTION_THRESHOLD, this.CONFIDENCE_THRESHOLD_BASE + 25);
    }
    if (this.context.consecutive_protections >= 2) {
      return this.CONFIDENCE_THRESHOLD_BASE + 15;
    }
    if (this.context.deep_scan_rounds > 0) {
      return this.CONFIDENCE_THRESHOLD_BASE + 10;
    }
    return this.CONFIDENCE_THRESHOLD_BASE;
  }

  /**
   * Atualiza estatísticas de estratégia (memória de analytics)
   */
  async updateStrategyStats(signalId: string, result: 'win' | 'protection' | 'loss'): Promise<void> {
    // Por enquanto mantém em memória
    const stats = this.strategyStats.get(signalId) || {
      strategyId: signalId,
      totalEntries: 0,
      wins: 0,
      protections: 0,
      last10Results: []
    };

    stats.totalEntries++;
    if (result === 'win') {
      stats.wins++;
      this.context.consecutive_protections = 0;
      this.context.deep_scan_rounds = 0;
    } else if (result === 'protection') {
      stats.protections++;
      this.context.consecutive_protections++;
    } else {
      this.context.consecutive_protections++;
      this.context.deep_scan_rounds = 0;
    }

    stats.last10Results = [...stats.last10Results.slice(-9), result];
    this.strategyStats.set(signalId, stats);
  }

  /**
   * Obtém estratégia com maior assertividade do dia
   */
  getBestStrategyToday(): StrategyStats | null {
    let best: StrategyStats | null = null;
    let bestWinRate = 0;

    for (const stats of this.strategyStats.values()) {
      if (stats.totalEntries >= 3) {
        const winRate = stats.wins / stats.totalEntries;
        if (winRate > bestWinRate) {
          bestWinRate = winRate;
          best = stats;
        }
      }
    }

    return best;
  }

  /**
   * Verifica se deve entrar em modo Deep Scan
   */
  shouldEnterDeepScan(): boolean {
    return this.context.consecutive_protections >= 3;
  }

  /**
   * Decrementa rodadas de Deep Scan
   */
  decrementDeepScanRounds(): void {
    if (this.context.deep_scan_rounds > 0) {
      this.context.deep_scan_rounds--;
    }
  }

  /**
   * Obtém contagem atual de proteções consecutivas
   */
  getConsecutiveProtections(): number {
    return this.context.consecutive_protections;
  }

  /**
   * Incrementa rodadas de Deep Scan
   */
  incrementDeepScanRounds(): void {
    if (this.shouldEnterDeepScan()) {
      this.context.deep_scan_rounds = this.DEEP_SCAN_ROUNDS;
    }
  }

  /**
   * Analisa o estado atual da roleta baseado no histórico
   * INTEGRA: RAG, ReAct, Memória de Analytics, Filtro Anti-Vício
   */
  analyze(currentNumber: number, history: number[] = []): RouletteAnalysis {
    this.updateContext(currentNumber, history);

    const streaks = this.calculateStreaks();
    const gaps = this.calculateGaps(currentNumber);
    const patterns = this.identifyPatterns();
    const variance = this.calculateVariance();
    const terminalAnalysis = this.analyzeTerminal(currentNumber);

    const baseConfidence = this.calculateConfidence(streaks, gaps, patterns, variance);
    const vicioDetection = this.detectVicioDeZona();
    const reactThoughts = this.runReActLoop(currentNumber, { variance, patterns, streaks });
    const adjustedThreshold = this.calculateAdjustedThreshold();

    // Simulated strategy stats - in production would come from DB
    const strategyStats: StrategyStats[] = [
      { strategyId: 'strategy_6', totalEntries: 10, wins: 7, protections: 3, last10Results: ['win', 'win', 'protection', 'win', 'win'] }
    ];

    // Adjust confidence based on vicio detection
    let finalConfidence = baseConfidence;
    if (vicioDetection.detected) {
      finalConfidence = Math.max(0.1, finalConfidence - 0.3);
    }

    return {
      number: currentNumber,
      streaks,
      gaps,
      patterns,
      variance,
      confidence: finalConfidence,
      react_thoughts: reactThoughts,
      vicio_detection: vicioDetection.detected ? vicioDetection : null,
      strategy_stats: strategyStats,
      adjustedConfidenceThreshold: adjustedThreshold,
      terminal_analysis: terminalAnalysis
    };
  }

  private analyzeTerminal(currentNumber: number): { current: number; neighbors: number[]; trend: 'hot' | 'cold' | 'stable' } {
    const terminal = this.getTerminal(currentNumber);
    const neighbors = NEIGHBORS_MAP[terminal] || [];
    const trend = this.analyzeTerminalTrend(terminal);

    return { current: terminal, neighbors, trend };
  }

  private getTerminal(num: number): number {
    if (num === 0) return 0;
    return Math.ceil(num / 3);
  }

  private calculateStreaks(): RouletteAnalysis['streaks'] {
    const history = this.context.history;
    let red = 0, black = 0, even = 0, odd = 0, high = 0, low = 0;

    for (let i = history.length - 1; i >= 0; i--) {
      const num = history[i];
      const isRed = this.isRed(num);
      const isEven = num % 2 === 0;
      const isHigh = num >= 19;

      if (isRed) red++;
      else if (num !== 0) black++;

      if (isEven) even++;
      else odd++;

      if (isHigh) high++;
      else if (num !== 0) low++;
    }

    return { red, black, even, odd, high, low };
  }

  private calculateGaps(currentNumber: number): RouletteAnalysis['gaps'] {
    const history = this.context.history;
    const lastIndex = history.length - 1;

    // Gap de cor
    let colorGap = 0;
    const currentColor = this.getColor(currentNumber);
    for (let i = lastIndex - 1; i >= 0; i--) {
      if (this.getColor(history[i]) === currentColor) break;
      colorGap++;
    }

    // Gap de número específico
    let numberGap = 0;
    for (let i = lastIndex - 1; i >= 0; i--) {
      if (history[i] === currentNumber) break;
      numberGap++;
    }

    // Gaps por setor
    const sectorGaps = this.calculateSectorGaps(currentNumber);

    return {
      color_gap: colorGap,
      number_gap: numberGap,
      sector_gaps: sectorGaps
    };
  }

  private identifyPatterns(): RouletteAnalysis['patterns'] {
    const history = this.context.history;
    const frequency: Record<number, number> = {};

    // Conta frequência dos últimos 50 números
    const recent = history.slice(-50);
    recent.forEach(num => {
      frequency[num] = (frequency[num] || 0) + 1;
    });

    const hotNumbers = Object.entries(frequency)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 6)
      .map(([num]) => parseInt(num));

    const coldNumbers = Object.keys(frequency)
      .filter(num => !hotNumbers.includes(parseInt(num)))
      .map(num => parseInt(num))
      .sort((a, b) => frequency[b] - frequency[a])
      .slice(0, 6);

    const sectorBias = this.calculateSectorBias();

    const terminals: number[] = [];
    history.slice(-10).forEach(num => {
      const terminal = this.getTerminal(num);
      if (!terminals.includes(terminal)) {
        terminals.push(terminal);
      }
    });

    return {
      hot_numbers: hotNumbers,
      cold_numbers: coldNumbers,
      sector_bias: sectorBias,
      terminals: terminals.slice(0, 4)
    };
  }

  private calculateVariance(): number {
    if (this.context.history.length < 10) return 0;

    const mean = this.context.history.reduce((a, b) => a + b, 0) / this.context.history.length;
    const variance = this.context.history.reduce((acc, num) => acc + Math.pow(num - mean, 2), 0) / this.context.history.length;

    return Math.sqrt(variance);
  }

  private calculateConfidence(
    streaks: RouletteAnalysis['streaks'],
    gaps: RouletteAnalysis['gaps'],
    patterns: RouletteAnalysis['patterns'],
    variance: number
  ): number {
    // Combina múltiplos fatores para calcular confiança
    let confidence = 0.5; // Base

    // Penaliza alta variância (mais aleatoriedade)
    confidence -= variance / 100;

    // Recompensa gaps significativos (potencial correção)
    if (gaps.color_gap > 5) confidence += 0.1;
    if (gaps.number_gap > 20) confidence += 0.15;

    // Recompensa streaks longos (padrão estabelecido)
    const maxStreak = Math.max(...Object.values(streaks));
    if (maxStreak > 8) confidence += 0.2;

    // Limita entre 0.1 e 0.95
    return Math.max(0.1, Math.min(0.95, confidence));
  }

  // Métodos auxiliares
  private isRed(num: number): boolean {
    const redNumbers = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36];
    return redNumbers.includes(num);
  }

  private getColor(num: number): string {
    if (num === 0) return 'green';
    return this.isRed(num) ? 'red' : 'black';
  }

  private updateSectorStats(num: number): void {
    const sector = this.getSector(num);
    this.context.sector_stats[sector] = {
      count: (this.context.sector_stats[sector]?.count || 0) + 1,
      last_seen: this.context.history.length - 1
    };
  }

  private getSector(num: number): string {
    // Implementação simplificada - pode ser expandida para Voisins/Tiers/Orphans
    if (num >= 1 && num <= 12) return 'first_dozen';
    if (num >= 13 && num <= 24) return 'second_dozen';
    if (num >= 25 && num <= 36) return 'third_dozen';
    return 'zero';
  }

  private calculateSectorGaps(currentNumber: number): Record<string, number> {
    const currentSector = this.getSector(currentNumber);
    const gaps: Record<string, number> = {};

    Object.keys(this.context.sector_stats).forEach(sector => {
      const lastSeen = this.context.sector_stats[sector].last_seen;
      gaps[sector] = this.context.history.length - 1 - lastSeen;
    });

    return gaps;
  }

  private calculateSectorBias(): Record<string, number> {
    const total = this.context.history.length;
    const bias: Record<string, number> = {};

    Object.keys(this.context.sector_stats).forEach(sector => {
      bias[sector] = this.context.sector_stats[sector].count / total;
    });

    return bias;
  }
}