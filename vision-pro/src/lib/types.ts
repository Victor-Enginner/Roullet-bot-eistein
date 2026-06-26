export interface Signal {
  id: string;
  number: number;
  strategy: string;
  confidence: number;
  reasoning: string;
  timestamp: number;
  entry: string[];
  protection: string[];
  status: 'IDLE' | 'ANALYZING' | 'SIGNAL_READY' | 'PROTECTION';
}

export interface Game {
  id: number;
  name: string;
  provider: string;
  status: 'active' | 'inactive';
}
