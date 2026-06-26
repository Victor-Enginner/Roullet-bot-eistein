'use client';

import { useEffect } from 'react';
import { useSignalStore } from '@/store/signalStore';
import { SignalCard } from '@/components/signal/SignalCard';
import { GameGrid } from '@/components/game/GameGrid';
import { MetricsPanel } from '@/components/dashboard/MetricsPanel';
import { StakeCalculator } from '@/components/dashboard/StakeCalculator';

export default function Dashboard() {
  const { connect, disconnect } = useSignalStore();

  useEffect(() => {
    connect();
    return () => disconnect();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-dark text-foreground">
      {/* Header */}
      <header className="border-b border-border p-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <h1 className="text-2xl font-bold neon-text">Vision Pro</h1>
          <div className="flex items-center space-x-4">
            <MetricsPanel />
            <StakeCalculator />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto p-6">
        {/* Signal Alert */}
        <SignalCard />

        {/* Games Grid */}
        <section className="mb-8">
          <h2 className="text-xl font-bold mb-4">Mesas Ativas</h2>
          <GameGrid />
        </section>

        {/* Additional Content */}
        <section className="grid md:grid-cols-2 gap-6">
          {/* Placeholder for more content */}
          <div className="bg-card rounded-lg p-6 border border-border">
            <h3 className="text-lg font-semibold mb-3">Análise em Tempo Real</h3>
            <p className="text-muted-foreground text-sm">
              Monitorando 4 mesas ativamente com latência &lt; 50ms
            </p>
          </div>
          <div className="bg-card rounded-lg p-6 border border-border">
            <h3 className="text-lg font-semibold mb-3">Performance da IA</h3>
            <p className="text-muted-foreground text-sm">
              Taxa de acerto: 87.3% | Últimas 24h
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}
