/**
 * Risk Agent - Gestão dinâmica de banca e risco adaptativo
 * Responsável por calcular stake sizes, stop loss, take profit,
 * e ajustar risco baseado no desempenho histórico e volatilidade.
 */

interface RiskParameters {
  baseStake: number;
  maxStake: number;
  bankroll: number;
  maxLoss: number;
  targetProfit: number;
}

interface RiskAssessment {
  recommendedStake: number;
  stopLoss: number;
  takeProfit: number;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'VERY_HIGH';
  reasoning: string;
  canProceed: boolean;
}

interface PerformanceMetrics {
  winRate: number;
  profitLoss: number;
  consecutiveLosses: number;
  volatility: number;
  sessionLength: number;
}

export class RiskAgent {
  private params: RiskParameters;
  private performance: PerformanceMetrics;

  constructor(params: RiskParameters) {
    this.params = params;
    this.performance = {
      winRate: 0.5,
      profitLoss: 0,
      consecutiveLosses: 0,
      volatility: 0,
      sessionLength: 0
    };
  }

  /**
   * Avalia risco para uma nova entrada baseada no contexto atual
   */
  assessRisk(confidence: number, analysis: any): RiskAssessment {
    // Calcula stake recomendado baseado em Kelly Criterion adaptado
    const recommendedStake = this.calculateStake(confidence);

    // Define stop loss baseado em risco máximo
    const stopLoss = this.calculateStopLoss();

    // Define take profit baseado em expectativa
    const takeProfit = this.calculateTakeProfit(confidence);

    // Avalia nível de risco geral
    const riskLevel = this.assessRiskLevel(confidence, analysis);

    // Gera explicação do raciocínio
    const reasoning = this.generateReasoning(recommendedStake, stopLoss, takeProfit, riskLevel);

    // Decide se pode prosseguir
    const canProceed = this.shouldProceed(riskLevel, recommendedStake);

    return {
      recommendedStake,
      stopLoss,
      takeProfit,
      riskLevel,
      reasoning,
      canProceed
    };
  }

  /**
   * Atualiza métricas de performance após resultado
   */
  updatePerformance(won: boolean, stake: number, payout: number): void {
    this.performance.sessionLength++;

    if (won) {
      this.performance.profitLoss += payout - stake;
      this.performance.consecutiveLosses = 0;
    } else {
      this.performance.profitLoss -= stake;
      this.performance.consecutiveLosses++;
    }

    // Recalcula win rate
    const totalTrades = this.performance.sessionLength;
    const wins = totalTrades - this.performance.consecutiveLosses; // Aproximado
    this.performance.winRate = wins / totalTrades;

    // Atualiza volatilidade (simplificada)
    this.performance.volatility = Math.abs(this.performance.profitLoss) / Math.max(1, totalTrades);
  }

  private calculateStake(confidence: number): number {
    // Kelly Criterion adaptado: f = (bp - q) / b
    // Onde: b = odds (aprox. 2 para vermelho/preto), p = probabilidade, q = 1-p

    const odds = 2; // Para apostas simples
    const probability = confidence;
    const q = 1 - probability;

    const kellyFraction = (odds * probability - q) / odds;

    // Ajusta baseado no bankroll e limita conservadoramente
    const maxKellyStake = this.params.bankroll * Math.min(kellyFraction, 0.05); // Máximo 5%

    // Ajusta baseado em performance recente
    const performanceMultiplier = this.getPerformanceMultiplier();

    const recommendedStake = Math.min(
      maxKellyStake * performanceMultiplier,
      this.params.maxStake,
      this.params.bankroll * 0.02 // Máximo 2% do bankroll
    );

    return Math.max(recommendedStake, this.params.baseStake);
  }

  private calculateStopLoss(): number {
    // Stop loss baseado em máximo loss permitido
    return Math.min(
      this.params.maxLoss,
      this.params.bankroll * 0.1 // Máximo 10% do bankroll
    );
  }

  private calculateTakeProfit(confidence: number): number {
    // Take profit baseado na confiança e expectativa
    const baseProfit = this.params.bankroll * 0.05; // 5% do bankroll
    const confidenceMultiplier = confidence / 0.5; // Multiplica se confiança > 50%

    return baseProfit * confidenceMultiplier;
  }

  private assessRiskLevel(confidence: number, analysis: any): 'LOW' | 'MEDIUM' | 'HIGH' | 'VERY_HIGH' {
    let riskScore = 0;

    // Confiança baixa aumenta risco
    if (confidence < 0.6) riskScore += 2;
    else if (confidence < 0.75) riskScore += 1;

    // Alta variância aumenta risco
    if (analysis.variance > 50) riskScore += 1;

    // Muitos losses consecutivos aumentam risco
    if (this.performance.consecutiveLosses >= 3) riskScore += 2;
    else if (this.performance.consecutiveLosses >= 1) riskScore += 1;

    // Win rate baixa aumenta risco
    if (this.performance.winRate < 0.4) riskScore += 1;

    // Mapeia score para nível
    if (riskScore >= 4) return 'VERY_HIGH';
    if (riskScore >= 3) return 'HIGH';
    if (riskScore >= 1) return 'MEDIUM';
    return 'LOW';
  }

  private getPerformanceMultiplier(): number {
    // Ajusta stake baseado em performance recente
    let multiplier = 1;

    if (this.performance.winRate > 0.6) multiplier *= 1.2;
    else if (this.performance.winRate < 0.4) multiplier *= 0.8;

    if (this.performance.consecutiveLosses >= 2) multiplier *= 0.7;
    else if (this.performance.profitLoss > this.params.bankroll * 0.1) multiplier *= 1.1;

    return Math.max(0.5, Math.min(2, multiplier));
  }

  private generateReasoning(
    stake: number,
    stopLoss: number,
    takeProfit: number,
    riskLevel: string
  ): string {
    const reasons = [];

    reasons.push(`Stake recomendado: R$ ${stake.toFixed(2)} baseado em Kelly Criterion adaptado`);

    if (this.performance.consecutiveLosses > 0) {
      reasons.push(`${this.performance.consecutiveLosses} losses consecutivos detectados - stake reduzido`);
    }

    reasons.push(`Stop Loss: R$ ${stopLoss.toFixed(2)} (${((stopLoss / this.params.bankroll) * 100).toFixed(1)}% do bankroll)`);
    reasons.push(`Take Profit: R$ ${takeProfit.toFixed(2)} (${((takeProfit / this.params.bankroll) * 100).toFixed(1)}% do bankroll)`);

    reasons.push(`Nível de risco: ${riskLevel}`);

    if (this.performance.winRate < 0.5) {
      reasons.push(`Win rate atual: ${(this.performance.winRate * 100).toFixed(1)}% - cautela recomendada`);
    }

    return reasons.join('. ');
  }

  private shouldProceed(riskLevel: string, stake: number): boolean {
    // Não prossegue em risco muito alto
    if (riskLevel === 'VERY_HIGH') return false;

    // Não prossegue se stake > 5% do bankroll
    if (stake > this.params.bankroll * 0.05) return false;

    // Não prossegue se stop loss seria atingido
    if (this.performance.profitLoss <= -this.params.maxLoss) return false;

    return true;
  }

  /**
   * Atualiza parâmetros de risco dinamicamente
   */
  updateParameters(newParams: Partial<RiskParameters>): void {
    this.params = { ...this.params, ...newParams };
  }

  /**
   * Reseta métricas de performance (novo dia/sessão)
   */
  resetPerformance(): void {
    this.performance = {
      winRate: 0.5,
      profitLoss: 0,
      consecutiveLosses: 0,
      volatility: 0,
      sessionLength: 0
    };
  }
}