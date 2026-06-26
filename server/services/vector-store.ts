/**
 * Vector Store Service - Integração RAG (Retrieval Augmented Generation)
 * Interface para consultar estratégias clássicas e comentários técnicos
 * salvos em Pinecone/Supabase Vector ou mock local.
 */

interface StrategyDocument {
  id: string;
  title: string;
  content: string;
  author: string;
  strategy_type: string;
  tags: string[];
  embedding?: number[]; // Para busca vetorial
}

interface RAGQuery {
  query: string;
  context?: string;
  strategyType?: string;
  limit?: number;
}

interface RAGResult {
  strategy: StrategyDocument;
  relevance: number;
  reasoning: string;
}

export class VectorStoreService {
  private mockStrategies: StrategyDocument[];

  constructor() {
    // Mock de estratégias clássicas - será substituído por Pinecone/Supabase
    this.mockStrategies = this.initializeMockStrategies();
  }

  /**
   * Busca estratégias relevantes baseadas na query RAG
   */
  async queryStrategies(query: RAGQuery): Promise<RAGResult[]> {
    // Simulação de busca vetorial - em produção usaria Pinecone/Supabase
    const results: RAGResult[] = [];

    // Busca por similaridade de texto (mock)
    for (const strategy of this.mockStrategies) {
      const relevance = this.calculateRelevance(query, strategy);

      if (relevance > 0.3) { // Threshold mínimo
        results.push({
          strategy,
          relevance,
          reasoning: this.generateReasoning(query, strategy, relevance)
        });
      }
    }

    // Ordena por relevância e limita
    return results
      .sort((a, b) => b.relevance - a.relevance)
      .slice(0, query.limit || 3);
  }

  /**
   * Busca estratégia específica por padrões detectados
   */
  async findStrategyForPattern(pattern: string, context: string): Promise<RAGResult | null> {
    const query: RAGQuery = {
      query: `estratégia para ${pattern} em ${context}`,
      limit: 1
    };

    const results = await this.queryStrategies(query);
    return results.length > 0 ? results[0] : null;
  }

  /**
   * Adiciona nova estratégia ao repositório (para aprendizado futuro)
   */
  async addStrategy(strategy: Omit<StrategyDocument, 'id'>): Promise<string> {
    const id = `strategy_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    const newStrategy: StrategyDocument = {
      id,
      ...strategy
    };

    this.mockStrategies.push(newStrategy);

    // Em produção: salvar no Pinecone/Supabase
    console.log(`Strategy added: ${id}`);

    return id;
  }

  /**
   * Atualiza estratégia existente
   */
  async updateStrategy(id: string, updates: Partial<StrategyDocument>): Promise<boolean> {
    const index = this.mockStrategies.findIndex(s => s.id === id);

    if (index === -1) return false;

    this.mockStrategies[index] = {
      ...this.mockStrategies[index],
      ...updates
    };

    return true;
  }

  private calculateRelevance(query: RAGQuery, strategy: StrategyDocument): number {
    let score = 0;

    // Busca por palavras-chave na query
    const queryWords = query.query.toLowerCase().split(' ');
    const content = strategy.content.toLowerCase();
    const title = strategy.title.toLowerCase();

    // Pontuação por matches no título (mais peso)
    for (const word of queryWords) {
      if (title.includes(word)) score += 0.3;
    }

    // Pontuação por matches no conteúdo
    for (const word of queryWords) {
      if (content.includes(word)) score += 0.1;
    }

    // Bônus por tipo de estratégia relevante
    if (query.strategyType && strategy.strategy_type === query.strategyType) {
      score += 0.2;
    }

    // Bônus por tags relevantes
    if (strategy.tags.some(tag => query.query.toLowerCase().includes(tag))) {
      score += 0.15;
    }

    return Math.min(1, score);
  }

  private generateReasoning(query: RAGQuery, strategy: StrategyDocument, relevance: number): string {
    const reasons = [];

    if (relevance > 0.8) {
      reasons.push("Excelente correspondência com padrões históricos");
    } else if (relevance > 0.6) {
      reasons.push("Boa adaptação para o contexto atual");
    } else {
      reasons.push("Possível alternativa baseada em princípios similares");
    }

    reasons.push(`Fonte: ${strategy.author} (${strategy.title})`);

    if (strategy.tags.length > 0) {
      reasons.push(`Tópicos relacionados: ${strategy.tags.join(', ')}`);
    }

    return reasons.join('. ');
  }

  private initializeMockStrategies(): StrategyDocument[] {
    return [
      {
        id: "martingale_classic",
        title: "Martingale Clássica",
        content: "A estratégia Martingale consiste em dobrar a aposta após cada perda, retornando ao stake inicial após vitória. Criada no século XVIII na França, visa recuperar perdas através do crescimento exponencial. Risco alto devido ao limite de mesa e bankroll finito.",
        author: "Sistema Tradicional",
        strategy_type: "progressive",
        tags: ["martingale", "progressiva", "recuperação", "alto-risco"]
      },
      {
        id: "james_bond_strategy",
        title: "Sistema James Bond",
        content: "Criado por Ian Fleming para seu personagem James Bond. Distribui 200 unidades: 140 no alto (19-36), 50 no meio (13-18), 10 no zero. Cobertura de 25 números com expectativa positiva. Menos arriscado que Martingale.",
        author: "Ian Fleming",
        strategy_type: "flat_betting",
        tags: ["james-bond", "cobertura", "baixo-risco", "distribuição"]
      },
      {
        id: "voisins_zero",
        title: "Voisins du Zero",
        content: "Sistema francês que cobre os 17 números vizinhos ao zero (22-25, 0, 26-32, 15-19, 4-8, 10-14, 2-7). Usa chips fracionados para apostas múltiplas. Estratégia de curto prazo baseada em setores quentes.",
        author: "Cassinos Franceses",
        strategy_type: "sector_betting",
        tags: ["voisins", "zero", "setor", "francês", "chip-fracionado"]
      },
      {
        id: "pattern_correction",
        title: "Correção de Padrões",
        content: "Baseada na lei dos grandes números, esta estratégia aposta contra padrões estabelecidos. Quando um cor surge 5+ vezes consecutivas, aposta na alternância. Confiança cresce com o tamanho do desvio estatístico.",
        author: "Análise Estatística Moderna",
        strategy_type: "pattern_betting",
        tags: ["correção", "estatística", "padrões", "probabilidade"]
      },
      {
        id: "fibonacci_progression",
        title: "Progressão Fibonacci",
        content: "Usa a sequência matemática de Fibonacci (1,1,2,3,5,8,13...) para ajustar stakes. Menos agressiva que Martingale, permite recuperação gradual. Ideal para jogadores conservadores com paciência.",
        author: "Sequência Matemática",
        strategy_type: "progressive",
        tags: ["fibonacci", "matemática", "conservador", "recuperação-gradual"]
      },
      {
        id: "sector_bias_tracking",
        title: "Rastreamento de Viés Setorial",
        content: "Monitora frequência de setores (dúzias/colunas) ao longo de 100+ giros. Identifica setores 'quentes' ou 'frios' e aposta na correção do viés. Estratégia baseada em análise de frequência empírica.",
        author: "Análise de Frequência",
        strategy_type: "sector_betting",
        tags: ["setor", "viés", "frequência", "análise-longa", "correção"]
      }
    ];
  }

  /**
   * Hook para futura integração multimodal (OCR/vision)
   */
  async queryByImage(imageData: Buffer, context?: string): Promise<RAGResult[]> {
    // TODO: Implementar análise de imagem da roleta
    // - OCR para detectar números
    // - Análise de padrões visuais
    // - Comparação com estratégias baseadas em observação visual

    console.log("Multimodal RAG: Análise de imagem não implementada ainda");
    return [];
  }
}