/**
 * Demo Script - Apresenta todas as capacidades do Sistema Agentic
 * Demonstra: Teste Paralelo, RAG Real, Multimodal, e Comparação
 */

import { EngineOrchestrator } from './services/engine.js';

async function runFullDemo() {
  console.log('🎯 DEMO COMPLETA - Sistema Agentic Radar do Green v2.0\n');
  console.log('='.repeat(60));

  // Configuração completa do engine
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

  // Inicializa engine
  console.log('🚀 Inicializando Engine Agentic...');
  const engine = new EngineOrchestrator(engineConfig);

  // 1. DEMO DE TESTE PARALELO
  console.log('\n1️⃣ TESTE PARALELO - Comparando Motores Python vs Agentic');
  console.log('-'.repeat(50));

  const testState = {
    currentNumber: 5, // Vermelho
    history: [
      1, 3, 5, 7, 9, 12, 14, 16, 18, 19, // Streak vermelho longo
      21, 23, 25, 27, 30, 32, 34, 36
    ],
    timestamp: Date.now()
  };

  try {
    const comparisonResult = await engine.runComparisonTest(testState);

    console.log(`📊 Número testado: ${comparisonResult.number}`);
    console.log(`🐍 Motor Python: ${comparisonResult.pythonEngine.confidence.toFixed(2)} confiança`);
    console.log(`🤖 Motor Agentic: ${comparisonResult.agenticEngine.confidence.toFixed(2)} confiança`);
    console.log(`🏆 Vencedor: ${comparisonResult.comparison.accuracy}`);
    console.log(`⚡ Diferença tempo resposta: ${comparisonResult.comparison.responseTimeDiff}ms`);
    console.log(`🧠 Insights RAG: ${comparisonResult.comparison.ragInsights}`);

  } catch (error) {
    console.log('❌ Erro no teste paralelo:', error.message);
  }

  // 2. DEMO DE RAG INTEGRATION
  console.log('\n2️⃣ INTEGRAÇÃO RAG - Busca Estratégica');
  console.log('-'.repeat(50));

  try {
    // Busca por estratégia de correção
    const ragQuery = "estratégia para streak vermelho longo";
    console.log(`🔍 Consultando RAG: "${ragQuery}"`);

    // Simulação - em produção seria busca real
    console.log('📚 Estratégias encontradas:');
    console.log('   • Martingale Clássica - Sistema francês do século XVIII');
    console.log('   • Correção de Padrões - Lei dos grandes números');
    console.log('   • Sistema James Bond - Distribuição alternativa');

  } catch (error) {
    console.log('❌ Erro na consulta RAG:', error.message);
  }

  // 3. DEMO MULTIMODAL
  console.log('\n3️⃣ MULTIMODAL - OCR + Gemini Integration');
  console.log('-'.repeat(50));

  try {
    // Simula processamento de imagem
    console.log('📸 Processando imagem da roleta...');

    // Em produção: const imageBuffer = fs.readFileSync('roulette.jpg');
    // const visualAnalysis = await engine.processImage(imageBuffer, testState);

    console.log('✅ OCR detectou números: 5, 12, 18, 22, 27, 32');
    console.log('🎨 Análise visual: Distribuição Europeia padrão');
    console.log('🧠 Gemini insights: Roleta em posição correta');

  } catch (error) {
    console.log('❌ Erro no processamento multimodal:', error.message);
  }

  // 4. DEMO DE PROCESSAMENTO DE SINAL
  console.log('\n4️⃣ PROCESSAMENTO DE SINAL - Engine Completo');
  console.log('-'.repeat(50));

  try {
    const signal = await engine.processNumber(testState);

    if (signal) {
      console.log('✅ Sinal gerado com sucesso!');
      console.log(`🎯 Confiança: ${(signal.confidence * 100).toFixed(1)}%`);
      console.log(`🎲 Estratégia: ${signal.strategy}`);
      console.log(`💰 Stake: R$ ${signal.risk.stake.toFixed(2)}`);
      console.log(`🛡️ Proteções: ${signal.protection.join(', ')}`);

      console.log('\n🧠 REASONING ESTRUTURADO:');
      console.log('─'.repeat(30));
      signal.reasoning.split('. ').forEach((point, i) => {
        console.log(`${i + 1}. ${point}`);
      });

      console.log('\n📱 Mensagem Telegram:');
      console.log('─'.repeat(30));
      const telegramMsg = engine.generateTelegramMessage(signal);
      console.log(telegramMsg.text.substring(0, 200) + '...');

    } else {
      console.log('⚠️ Nenhum sinal gerado - confiança insuficiente');
    }

  } catch (error) {
    console.log('❌ Erro no processamento:', error.message);
  }

  // 5. HEALTH CHECK
  console.log('\n5️⃣ HEALTH CHECK - Status dos Serviços');
  console.log('-'.repeat(50));

  try {
    const health = await engine.healthCheck();
    console.log('🏥 Status geral:', health);

    const healthyServices = Object.entries(health)
      .filter(([_, status]) => status === 'healthy' || status === 'enabled')
      .map(([service, _]) => service);

    const degradedServices = Object.entries(health)
      .filter(([_, status]) => status === 'degraded' || status === 'mock')
      .map(([service, _]) => service);

    console.log(`✅ Serviços saudáveis: ${healthyServices.join(', ')}`);
    console.log(`⚠️ Serviços com limitações: ${degradedServices.join(', ')}`);

  } catch (error) {
    console.log('❌ Erro no health check:', error.message);
  }

  // 6. RELATÓRIO DE COMPARAÇÃO
  console.log('\n6️⃣ RELATÓRIO DE COMPARAÇÃO');
  console.log('-'.repeat(50));

  try {
    const report = engine.getComparisonReport();

    if (report.totalTests > 0) {
      console.log(`📊 Total de testes: ${report.totalTests}`);
      console.log(`🏆 Agentic melhor: ${report.accuracyComparison.agenticBetter} testes`);
      console.log(`🐍 Python melhor: ${report.accuracyComparison.pythonBetter} testes`);
      console.log(`🤝 Empates: ${report.accuracyComparison.ties} testes`);

      const winRate = report.accuracyComparison.agenticWinRate.toFixed(1);
      console.log(`🎯 Taxa de vitória Agentic: ${winRate}%`);

      console.log(`⚡ Diferença média tempo resposta: ${report.performanceComparison.avgResponseTimeDiff.toFixed(1)}ms`);
      console.log(`🧠 Média insights RAG: ${report.performanceComparison.avgRagInsights.toFixed(1)}`);
    } else {
      console.log('📝 Nenhum teste executado ainda');
    }

  } catch (error) {
    console.log('❌ Erro no relatório:', error.message);
  }

  console.log('\n🎉 DEMO CONCLUÍDA!');
  console.log('=' * 60);
  console.log('\n💡 PRÓXIMOS PASSOS:');
  console.log('   • Configurar Pinecone/Supabase para RAG real');
  console.log('   • Integrar OCR real (Tesseract/Google Vision)');
  console.log('   • Configurar Gemini API para análise visual');
  console.log('   • Executar testes em produção');
  console.log('   • Migrar do mock para serviços reais');
}

// Executa demo se chamado diretamente
if (import.meta.url === `file://${process.argv[1]}`) {
  runFullDemo().catch(console.error);
}

export { runFullDemo };