import express from 'express';
import { EngineOrchestrator } from './services/engine.js';

const app = express();
app.use(express.json());

// Configuração do engine
const engineConfig = {
  minConfidence: 0.6,
  riskParams: {
    baseStake: 10,
    maxStake: 100,
    bankroll: 1000,
    maxLoss: 100,
    targetProfit: 50
  },
  enableRAG: true,
  enableLogging: true,
  enableComparison: true,
  enableMultimodal: true,
  deepScanProtectionThreshold: 3,
  vicioDetectionEnabled: true
};

// Inicializa o engine
const engine = new EngineOrchestrator(engineConfig);

// Endpoint para testar o reasoning estruturado
app.post('/test-reasoning', async (req, res) => {
  try {
    // Cenário de teste: Roleta com streak de vermelho
    const testState = {
      currentNumber: 5, // Vermelho
      history: [
        1, 3, 5, 7, 9, 12, 14, 16, 18, 19, // 10 vermelhos consecutivos
        21, 23, 25, 27, 30, 32, 34, 36     // Continua vermelho
      ],
      timestamp: Date.now()
    };

    console.log('🚀 Testando Engine Agentic...\n');

    // Processa o sinal
    const signal = await engine.processNumber(testState);

    if (!signal) {
      return res.json({
        success: false,
        message: 'Nenhum sinal gerado - confiança insuficiente'
      });
    }

    // Quebra o reasoning em etapas lógicas
    const breakdown = breakDownReasoning(signal);

    // Gera mensagem Telegram
    const telegramMsg = engine.generateTelegramMessage(signal);

    res.json({
      success: true,
      signal,
      reasoningBreakdown: breakdown,
      telegramMessage: telegramMsg.text
    });

  } catch (error) {
    console.error('Erro no teste:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

function breakDownReasoning(signal: any) {
  return {
    step1_whatHappened: {
      title: "1) O QUE ACONTECEU NA ROLETA",
      points: [
        `Número base: ${signal.number}`,
        "Histórico recente mostra padrão específico de streak",
        "Análise estatística detectou anomalias no comportamento"
      ]
    },
    step2_whyOpportunity: {
      title: "2) POR QUE CRIA OPORTUNIDADE",
      points: [
        "Desvio estatístico identificado (streak longo)",
        "Lei dos grandes números sugere correção natural",
        "Baseado em estratégias históricas testadas (Martingale reverso)"
      ]
    },
    step3_probabilityCalculated: {
      title: "3) QUAL A PROBABILIDADE CALCULADA",
      points: [
        `Confiança do agente: ${(signal.confidence * 100).toFixed(1)}%`,
        "Fatores considerados: streaks, gaps, variância estatística",
        "Threshold mínimo de segurança respeitado"
      ]
    },
    step4_howToEnter: {
      title: "4) COMO DEVEMOS ENTRAR",
      points: [
        `Estratégia selecionada: ${signal.strategy}`,
        `Entrada recomendada: ${signal.entry.join(', ')}`,
        `Proteções: ${signal.protection.join(', ')}`,
        `Stake calculado: R$ ${signal.risk.stake.toFixed(2)}`
      ]
    },
    fullReasoning: signal.reasoning.split('. ').map((point: string, i: number) => `${i + 1}. ${point}`)
  };
}

const port = 5000;
app.listen(port, () => {
  console.log(`Test server running on port ${port}`);
  console.log(`Test endpoint: POST http://localhost:${port}/test-reasoning`);
});