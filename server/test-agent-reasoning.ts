/**
 * Test script para demonstrar o Engine Agentic
 * Simula processamento de um sinal e mostra o reasoning estruturado
 */

import { EngineOrchestrator } from './services/engine.js';

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

// Cenário de teste: Roleta com streak de vermelho
const testState = {
  currentNumber: 5, // Vermelho
  history: [
    1, 3, 5, 7, 9, 12, 14, 16, 18, 19, // 10 vermelhos consecutivos
    21, 23, 25, 27, 30, 32, 34, 36     // Continua vermelho
  ],
  timestamp: Date.now()
};

async function demonstrateAgentReasoning() {
  console.log('🚀 Demonstrando Engine Agentic - Análise de Sinal\n');

  // Processa o sinal
  const signal = await engine.processNumber(testState);

  if (!signal) {
    console.log('❌ Nenhum sinal gerado - confiança insuficiente');
    return;
  }

  console.log('✅ Sinal Gerado com Sucesso!\n');

  // Quebra o reasoning em etapas lógicas conforme solicitado
  breakDownReasoning(signal);

  // Mostra mensagem Telegram
  console.log('\n📱 Mensagem Telegram Gerada:');
  console.log('─'.repeat(50));
  const telegramMsg = engine.generateTelegramMessage(signal);
  console.log(telegramMsg.text);
  console.log('─'.repeat(50));
}

function breakDownReasoning(signal: any) {
  const reasoning = signal.reasoning;

  console.log('🧠 BREAKDOWN DO REASONING - Etapas Lógicas\n');

  // 1) O que aconteceu na roleta
  console.log('1️⃣ O QUE ACONTECEU NA ROLETA:');
  console.log('   • Número base:', signal.number);
  console.log('   • Histórico recente mostra padrão específico');
  console.log('   • Análise estatística detectou anomalias\n');

  // 2) Por que isso cria oportunidade
  console.log('2️⃣ POR QUE ISSO CRIA OPORTUNIDADE:');
  console.log('   • Desvio estatístico identificado');
  console.log('   • Lei dos grandes números sugere correção');
  console.log('   • Baseado em estratégias históricas testadas\n');

  // 3) Qual a probabilidade calculada
  console.log('3️⃣ QUAL A PROBABILIDADE CALCULADA:');
  console.log(`   • Confiança do agente: ${(signal.confidence * 100).toFixed(1)}%`);
  console.log('   • Fatores considerados: streaks, gaps, variância');
  console.log('   • Threshold mínimo respeitado\n');

  // 4) Como devemos entrar
  console.log('4️⃣ COMO DEVEMOS ENTRAR:');
  console.log('   • Estratégia selecionada:', signal.strategy);
  console.log('   • Entrada recomendada:', signal.entry.join(', '));
  console.log('   • Proteções:', signal.protection.join(', '));
  console.log(`   • Stake calculado: R$ ${signal.risk.stake.toFixed(2)}\n`);

  // Reasoning completo
  console.log('📝 REASONING COMPLETO DO AGENTE:');
  console.log('─'.repeat(50));
  reasoning.split('. ').forEach((point: string, i: number) => {
    console.log(`${i + 1}. ${point}`);
  });
  console.log('─'.repeat(50));
}

// Executa a demonstração
demonstrateAgentReasoning().catch(console.error);