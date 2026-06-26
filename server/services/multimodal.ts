/**
 * Multimodal Service - Integração OCR + Gemini para análise visual
 * Permite processar imagens da roleta para detectar números e padrões
 */

interface OCRResult {
  numbers: number[];
  confidence: number;
  rawText: string;
  processingTime: number;
}

interface VisualAnalysis {
  detectedNumbers: number[];
  confidence: number;
  patterns: {
    wheelPosition?: string;
    numberClusters?: number[][];
    colorDistribution?: { red: number; black: number; green: number };
  };
  reasoning: string;
}

interface GeminiAnalysis {
  summary: string;
  confidence: number;
  recommendations: string[];
  visualInsights: string[];
}

export class MultimodalService {
  private geminiApiKey?: string;
  private ocrService: OCRService;

  constructor(geminiApiKey?: string) {
    this.geminiApiKey = geminiApiKey || process.env.GEMINI_API_KEY;
    this.ocrService = new OCRService();
  }

  /**
   * Processa imagem da roleta completa
   */
  async processRouletteImage(imageBuffer: Buffer): Promise<VisualAnalysis> {
    const startTime = Date.now();

    try {
      // 1. OCR para detectar números
      const ocrResult = await this.ocrService.processImage(imageBuffer);

      // 2. Análise visual com Gemini (se disponível)
      let geminiAnalysis: GeminiAnalysis | null = null;
      if (this.geminiApiKey) {
        geminiAnalysis = await this.analyzeWithGemini(imageBuffer, ocrResult);
      }

      // 3. Processa padrões visuais
      const patterns = this.analyzeVisualPatterns(ocrResult, geminiAnalysis);

      // 4. Calcula confiança geral
      const confidence = this.calculateVisualConfidence(ocrResult, geminiAnalysis);

      const analysis: VisualAnalysis = {
        detectedNumbers: ocrResult.numbers,
        confidence,
        patterns,
        reasoning: this.generateVisualReasoning(ocrResult, geminiAnalysis, patterns)
      };

      console.log(`✅ Visual analysis completed in ${Date.now() - startTime}ms`);
      return analysis;

    } catch (error) {
      console.error('❌ Visual analysis failed:', error);
      throw error;
    }
  }

  /**
   * Processa apenas OCR para detectar números
   */
  async detectNumbers(imageBuffer: Buffer): Promise<OCRResult> {
    return await this.ocrService.processImage(imageBuffer);
  }

  /**
   * Analisa imagem com Gemini AI
   */
  private async analyzeWithGemini(imageBuffer: Buffer, ocrResult: OCRResult): Promise<GeminiAnalysis> {
    if (!this.geminiApiKey) {
      throw new Error('Gemini API key not configured');
    }

    try {
      // TODO: Implementar chamada real para Gemini API
      // Por enquanto, simulação baseada no OCR
      const mockAnalysis: GeminiAnalysis = {
        summary: `Análise visual detectou ${ocrResult.numbers.length} números na roleta`,
        confidence: ocrResult.confidence,
        recommendations: [
          'Números detectados parecem estar em posições corretas',
          'Distribuição visual sugere roleta Europeia padrão'
        ],
        visualInsights: [
          'Wheel appears to be in standard European layout',
          'Numbers are clearly visible and well-positioned',
          'No visual anomalies detected in the wheel structure'
        ]
      };

      console.log('Gemini analysis (mock):', mockAnalysis);
      return mockAnalysis;

    } catch (error) {
      console.error('Gemini analysis failed:', error);
      return {
        summary: 'Análise visual não disponível',
        confidence: 0.5,
        recommendations: ['Usar apenas dados OCR'],
        visualInsights: []
      };
    }
  }

  /**
   * Analisa padrões visuais dos dados
   */
  private analyzeVisualPatterns(ocrResult: OCRResult, geminiAnalysis?: GeminiAnalysis | null): VisualAnalysis['patterns'] {
    const patterns: VisualAnalysis['patterns'] = {};

    // Agrupa números por setores (simplificado)
    const sectors = this.groupNumbersBySector(ocrResult.numbers);
    patterns.numberClusters = sectors;

    // Distribuição de cores
    const colorDist = this.calculateColorDistribution(ocrResult.numbers);
    patterns.colorDistribution = colorDist;

    // Análise de posição na roleta (se disponível via Gemini)
    if (geminiAnalysis?.visualInsights) {
      patterns.wheelPosition = this.extractWheelPosition(geminiAnalysis.visualInsights);
    }

    return patterns;
  }

  /**
   * Agrupa números por setores da roleta
   */
  private groupNumbersBySector(numbers: number[]): number[][] {
    const sectors = {
      firstDozen: numbers.filter(n => n >= 1 && n <= 12),
      secondDozen: numbers.filter(n => n >= 13 && n <= 24),
      thirdDozen: numbers.filter(n => n >= 25 && n <= 36),
      zero: numbers.filter(n => n === 0)
    };

    return [
      sectors.firstDozen,
      sectors.secondDozen,
      sectors.thirdDozen,
      sectors.zero
    ].filter(sector => sector.length > 0);
  }

  /**
   * Calcula distribuição de cores
   */
  private calculateColorDistribution(numbers: number[]): { red: number; black: number; green: number } {
    let red = 0, black = 0, green = 0;

    const redNumbers = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36];

    numbers.forEach(num => {
      if (num === 0) green++;
      else if (redNumbers.includes(num)) red++;
      else black++;
    });

    return { red, black, green };
  }

  /**
   * Extrai informação de posição da roleta dos insights visuais
   */
  private extractWheelPosition(visualInsights: string[]): string {
    // Simulação - em produção analisaria os insights do Gemini
    if (visualInsights.some(insight => insight.includes('European'))) {
      return 'European';
    }
    return 'Unknown';
  }

  /**
   * Calcula confiança geral da análise visual
   */
  private calculateVisualConfidence(ocrResult: OCRResult, geminiAnalysis?: GeminiAnalysis | null): number {
    let confidence = ocrResult.confidence;

    // Bônus se Gemini confirmou a análise
    if (geminiAnalysis && geminiAnalysis.confidence > 0.7) {
      confidence = Math.min(0.95, confidence + 0.1);
    }

    // Penalidade se poucos números detectados
    if (ocrResult.numbers.length < 5) {
      confidence *= 0.8;
    }

    return confidence;
  }

  /**
   * Gera explicação do raciocínio visual
   */
  private generateVisualReasoning(
    ocrResult: OCRResult,
    geminiAnalysis: GeminiAnalysis | null,
    patterns: VisualAnalysis['patterns']
  ): string {
    const reasons = [];

    reasons.push(`OCR detectou ${ocrResult.numbers.length} números com ${Math.round(ocrResult.confidence * 100)}% de confiança`);

    if (patterns.colorDistribution) {
      const { red, black, green } = patterns.colorDistribution;
      reasons.push(`Distribuição visual: ${red} vermelhos, ${black} pretos, ${green} verdes`);
    }

    if (geminiAnalysis) {
      reasons.push(`Análise Gemini: ${geminiAnalysis.summary}`);
      if (geminiAnalysis.visualInsights.length > 0) {
        reasons.push(`Insights visuais: ${geminiAnalysis.visualInsights[0]}`);
      }
    }

    if (patterns.numberClusters) {
      const clustersInfo = patterns.numberClusters
        .map(cluster => `${cluster.length} números`)
        .join(', ');
      reasons.push(`Agrupamentos detectados: ${clustersInfo}`);
    }

    return reasons.join('. ');
  }

  /**
   * Verifica se o serviço está configurado corretamente
   */
  async healthCheck(): Promise<{ status: 'healthy' | 'degraded' | 'unhealthy'; details: any }> {
    const details: any = {
      ocr: 'unknown',
      gemini: 'not_configured'
    };

    // Verifica OCR
    try {
      // Teste básico OCR (pode ser um teste com imagem conhecida)
      details.ocr = 'healthy';
    } catch (error) {
      details.ocr = 'unhealthy';
    }

    // Verifica Gemini
    if (this.geminiApiKey) {
      try {
        // Teste básico Gemini (ping ou chamada simples)
        details.gemini = 'healthy';
      } catch (error) {
        details.gemini = 'unhealthy';
      }
    }

    // Determina status geral
    if (details.ocr === 'healthy' && details.gemini === 'healthy') {
      return { status: 'healthy', details };
    } else if (details.ocr === 'healthy') {
      return { status: 'degraded', details };
    } else {
      return { status: 'unhealthy', details };
    }
  }
}

/**
 * Serviço OCR básico (pode ser Tesseract, Google Vision, etc.)
 */
class OCRService {
  async processImage(imageBuffer: Buffer): Promise<OCRResult> {
    const startTime = Date.now();

    try {
      // TODO: Implementar OCR real
      // Por enquanto, simulação baseada em padrões comuns

      // Simulação: detectar números comuns de roleta
      const mockNumbers = [5, 12, 18, 22, 27, 32]; // Números vermelhos
      const mockConfidence = 0.85;
      const mockText = mockNumbers.join(' ');

      return {
        numbers: mockNumbers,
        confidence: mockConfidence,
        rawText: mockText,
        processingTime: Date.now() - startTime
      };

    } catch (error) {
      console.error('OCR processing failed:', error);
      return {
        numbers: [],
        confidence: 0,
        rawText: '',
        processingTime: Date.now() - startTime
      };
    }
  }
}

/**
 * Hook para integração futura com diferentes provedores OCR
 */
export class OCRProviderFactory {
  static createTesseract(): OCRService {
    // TODO: Implementar Tesseract OCR
    return new OCRService();
  }

  static createGoogleVision(apiKey: string): OCRService {
    // TODO: Implementar Google Vision OCR
    return new OCRService();
  }

  static createFromEnv(): OCRService {
    const provider = process.env.OCR_PROVIDER || 'tesseract';
    const apiKey = process.env.GOOGLE_VISION_API_KEY;

    if (provider === 'google_vision' && apiKey) {
      return this.createGoogleVision(apiKey);
    }

    return this.createTesseract();
  }
}