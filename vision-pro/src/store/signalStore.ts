import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import io, { Socket } from 'socket.io-client';

interface Signal {
  id: string;
  number: number;
  strategy: string;
  confidence: number;
  timestamp: number;
  entry: string[];
  protection: string[];
  status: 'IDLE' | 'ANALYZING' | 'SIGNAL_READY' | 'PROTECTION';
}

interface SignalStore {
  socket: Socket | null;
  signals: Signal[];
  activeSignal: Signal | null;
  serverStatus: 'connected' | 'disconnected' | 'analyzing';
  connectionCount: number;
  
  // Actions
  connect: () => void;
  disconnect: () => void;
  addSignal: (signal: Omit<Signal, 'id' | 'timestamp'>) => void;
  clearActiveSignal: () => void;
  setServerStatus: (status: 'connected' | 'disconnected' | 'analyzing') => void;
}

export const useSignalStore = create<SignalStore>()(
  subscribeWithSelector((set, get) => ({
    socket: null,
    signals: [],
    activeSignal: null,
    serverStatus: 'disconnected',
    connectionCount: 0,

    connect: () => {
      const socket = io('http://localhost:4000');

      socket.on('connect', () => {
        set({ serverStatus: 'connected', connectionCount: get().connectionCount + 1 });
      });

      socket.on('disconnect', () => {
        set({ serverStatus: 'disconnected' });
      });

      socket.on('signal', (signal) => {
        const newSignal: Signal = {
          ...signal,
          id: Math.random().toString(36).substr(2, 9),
          timestamp: Date.now(),
          reasoning: signal.reasoning || 'Análise em processamento...',
          status: 'SIGNAL_READY'
        };
        
        set(state => ({
          signals: [newSignal, ...state.signals.slice(0, 49)],
          activeSignal: newSignal,
          serverStatus: 'analyzing'
        }));

        setTimeout(() => {
          set({ serverStatus: 'connected' });
        }, 2000);

        // Haptic feedback
        if ('vibrate' in navigator && signal.confidence > 0.85) {
          navigator.vibrate([100, 50, 100]);
        }
      });

      set({ socket });
    },

    disconnect: () => {
      get().socket?.disconnect();
      set({ socket: null, serverStatus: 'disconnected' });
    },

    addSignal: (signal) => {
      const newSignal: Signal = {
        ...signal,
        id: Math.random().toString(36).substr(2, 9),
        timestamp: Date.now(),
        reasoning: signal.reasoning || 'Sinal gerado manualmente',
        status: 'SIGNAL_READY'
      };
      
      set(state => ({
        signals: [newSignal, ...state.signals.slice(0, 49)],
        activeSignal: newSignal
      }));
    },

    clearActiveSignal: () => {
      set({ activeSignal: null });
    },

    setServerStatus: (status) => {
      set({ serverStatus: status });
    }
  }))
);
