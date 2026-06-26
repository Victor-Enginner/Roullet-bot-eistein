import { useState, useEffect, useRef } from "react";
import { useHealth } from "@/hooks/use-radar";
import { useMetrics } from "@/hooks/use-metrics";
import { MessageCircle, X, Bot, ChevronDown, Sparkles, Zap, TrendingUp, Shield, Eye, Brain } from "lucide-react";

interface Message {
  id: number;
  text: string;
  type: "bot" | "alert" | "thinking" | "deep_scan" | "abort";
  time: string;
  confidence?: number;
}

const INITIAL_MESSAGES: Message[] = [
  {
    id: 1,
    text: "🧠 Sistema RADAR DO GREEN v2.0 | Analista VIP inicializado.",
    type: "bot",
    time: now(),
  },
  {
    id: 2,
    text: "🤖 Mode: Pensamento -> Ação -> Observação ativo.",
    type: "thinking",
    time: now(),
  },
  {
    id: 3,
    text: "🛡️ Filtro Anti-Manipulação: Monitorando vícios de zona.",
    type: "bot",
    time: now(),
  },
];

function now() {
  return new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

const PATTERN_MESSAGES = [
  "📊 Padrão de alta assertividade detectado! Verificando Terminal + Vizinhos...",
  "🔍 Deep Scan: Analisando 5 rodadas para confirmar estabilização...",
  "⚠️ Vício de zona detectado! Abortando entrada para evitar Loss.",
  "🎯 Terminal quente identificado. Preparando sinal com confiança 90%+...",
  "🛡️ 3 proteções seguidas: Aumentando limiar de confiança para 95%.",
  "📈 Análise de setor concluída. Confiança acima de 80% detectada.",
  "⏳ Mesa fria há mais de 8 rodadas. Possível virada de tendência!",
  "💭 Pensamento: 'Observei que a bolinha insiste na zona do 11...'",
];

const REACTIVE_MESSAGES = {
  deep_scan: "🔍 Deep Scan ativo! Detectamos 3 proteções consecutivas. Aguardando 5 rodadas para estabilização antes de liberar próximo sinal.",
  vicio_zone: "⚠️ ALERTA: A bolinha está insistindo na mesma zona. Vou aguardar para confirmar mudança de tendência.",
  high_confidence: "🎯 CONFIA! Terminal + Vizinhos coincidem com quebra de tendência. Preparando entrada...",
  aborted: "🛑 Sinal ABORTADO: Padrão de vício detectado na região.",
  waiting: "⏳ Aguardando... padrão não favorável neste momento.",
};

export function AnalistaVIP() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
  const [typing, setTyping] = useState(false);
  const [unread, setUnread] = useState(0);
  const [agentState, setAgentState] = useState<'analyzing' | 'waiting' | 'deep_scan' | 'signal_ready'>('analyzing');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const { data: health } = useHealth();
  const { data: metrics } = useMetrics();

  // Auto scroll to bottom
  useEffect(() => {
    if (open) messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open]);

  // Push contextual messages every 25-40s
  useEffect(() => {
    const scheduleNext = () => {
      const delay = 25000 + Math.random() * 15000;
      intervalRef.current = setTimeout(() => {
        const isActive = health?.radarActive;
        const winRate = metrics?.winRate ?? 0;

        let text: string;
        let msgType: Message['type'] = 'bot';

        if (agentState === 'deep_scan') {
          text = REACTIVE_MESSAGES.deep_scan;
          msgType = 'deep_scan';
        } else if (agentState === 'signal_ready') {
          text = PATTERN_MESSAGES[3]; // High confidence message
          msgType = 'bot';
        } else if (isActive && winRate >= 60) {
          text = PATTERN_MESSAGES[Math.floor(Math.random() * 4)];
        } else if (!isActive) {
          text = "Radar em standby. Ative o RADAR DO GREEN para análise em tempo real.";
        } else {
          text = PATTERN_MESSAGES[4 + Math.floor(Math.random() * 4)];
        }

        setTyping(true);
        setTimeout(() => {
          setTyping(false);
          const newMsg: Message = { id: Date.now(), text, type: msgType, time: now() };
          setMessages((prev) => [...prev.slice(-12), newMsg]);
          if (!open) setUnread((n) => n + 1);
        }, 1800);

        scheduleNext();
      }, delay);
    };

    scheduleNext();
    return () => { if (intervalRef.current) clearTimeout(intervalRef.current); };
  }, [health?.radarActive, metrics?.winRate, open, agentState]);

  // Push alert when radar status changes
  useEffect(() => {
    if (health?.radarActive) {
      const msg: Message = {
        id: Date.now(),
        text: "🚨 RADAR ATIVADO! Modo Deep Scan disponível. Filtrando vícios de zona...",
        type: "alert",
        time: now(),
      };
      setMessages((prev) => [...prev.slice(-12), msg]);
      if (!open) setUnread((n) => n + 1);
      setAgentState('analyzing');
    }
  }, [health?.radarActive]);

  const handleOpen = () => {
    setOpen(true);
    setUnread(0);
  };

  return (
    <>
      {/* Floating button */}
      <button
        onClick={open ? () => setOpen(false) : handleOpen}
        className={`
          fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full
          flex items-center justify-center transition-all duration-300
          bg-primary border-2 border-primary/80
          shadow-[0_0_30px_rgba(34,197,94,0.5),0_4px_20px_rgba(0,0,0,0.5)]
          hover:shadow-[0_0_50px_rgba(34,197,94,0.7),0_4px_24px_rgba(0,0,0,0.5)]
          hover:scale-110 active:scale-95
        `}
        aria-label="Analista VIP"
      >
        {open ? (
          <ChevronDown className="w-6 h-6 text-black font-bold" />
        ) : (
          <Bot className="w-6 h-6 text-black font-bold" />
        )}
        {/* Unread badge */}
        {!open && unread > 0 && (
          <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-yellow-500 text-black text-xs font-black flex items-center justify-center shadow-lg">
            {unread > 9 ? "9+" : unread}
          </div>
        )}
        {/* Pulse ring when active */}
        {health?.radarActive && !open && (
          <div className="absolute inset-0 rounded-full border-2 border-primary/40 animate-ping" />
        )}
      </button>

      {/* Chat window */}
      <div
        className={`
          fixed bottom-24 right-6 z-50 w-80 rounded-2xl overflow-hidden
          transition-all duration-400 origin-bottom-right
          shadow-[0_20px_60px_rgba(0,0,0,0.6),0_0_40px_rgba(34,197,94,0.15)]
          border border-primary/20
          ${open ? "scale-100 opacity-100 pointer-events-auto" : "scale-90 opacity-0 pointer-events-none"}
        `}
        style={{ backdropFilter: "blur(20px)" }}
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-primary/20 to-primary/8 border-b border-primary/20 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="relative">
              <div className="w-8 h-8 rounded-full bg-primary/20 border border-primary/40 flex items-center justify-center">
                <Bot className="w-4 h-4 text-primary" />
              </div>
              <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-primary border border-black live-dot" />
            </div>
            <div>
              <p className="text-xs font-display text-white tracking-wider">ANALISTA VIP</p>
              <p className="text-xs text-primary font-bold">IA Ativa · RADAR DO GREEN</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Sparkles className="w-3.5 h-3.5 text-yellow-500" />
            <button onClick={() => setOpen(false)} className="text-zinc-500 hover:text-white transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="h-64 overflow-y-auto bg-black/80 px-4 py-3 space-y-3 flex flex-col">
          {messages.map((msg) => (
            <div key={msg.id} className="flex gap-2 items-start animate-in slide-in-from-bottom-2 duration-300">
              <div className={`w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center mt-0.5 ${
                msg.type === "alert" 
                  ? "bg-destructive/20 border border-destructive/40" 
                  : msg.type === "thinking"
                  ? "bg-blue-500/20 border border-blue-500/40"
                  : msg.type === "deep_scan"
                  ? "bg-purple-500/20 border border-purple-500/40"
                  : msg.type === "abort"
                  ? "bg-orange-500/20 border border-orange-500/40"
                  : "bg-primary/20 border border-primary/30"
              }`}>
                {msg.type === "alert" ? (
                  <Zap className="w-3 h-3 text-destructive" />
                ) : msg.type === "thinking" ? (
                  <Brain className="w-3 h-3 text-blue-400" />
                ) : msg.type === "deep_scan" ? (
                  <Eye className="w-3 h-3 text-purple-400" />
                ) : msg.type === "abort" ? (
                  <Shield className="w-3 h-3 text-orange-400" />
                ) : (
                  <Bot className="w-3 h-3 text-primary" />
                )}
              </div>
              <div className="flex-1">
                <div className={`rounded-xl rounded-tl-none px-3 py-2 text-xs leading-relaxed ${
                  msg.type === "alert"
                    ? "bg-destructive/10 border border-destructive/20 text-white"
                    : msg.type === "thinking"
                    ? "bg-blue-500/10 border border-blue-500/20 text-blue-100"
                    : msg.type === "deep_scan"
                    ? "bg-purple-500/10 border border-purple-500/20 text-purple-100"
                    : msg.type === "abort"
                    ? "bg-orange-500/10 border border-orange-500/20 text-orange-100"
                    : "bg-primary/8 border border-primary/15 text-zinc-200"
                }`}>
                  {msg.text}
                </div>
                <p className="text-xs text-zinc-700 mt-1 ml-1 font-medium">{msg.time}</p>
              </div>
            </div>
          ))}

          {/* Typing indicator */}
          {typing && (
            <div className="flex gap-2 items-start animate-in slide-in-from-bottom-2 duration-200">
              <div className="w-6 h-6 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center">
                <Bot className="w-3 h-3 text-primary" />
              </div>
              <div className="bg-primary/8 border border-primary/15 rounded-xl rounded-tl-none px-3 py-2">
                <div className="flex gap-1 items-center h-4">
                  <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "0ms" }} />
                  <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "150ms" }} />
                  <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Footer */}
        <div className="bg-black/90 border-t border-white/5 px-4 py-2 flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <TrendingUp className="w-3 h-3 text-primary" />
            <span className="text-xs font-bold text-primary">
              {metrics?.winRate ?? 0}% win rate
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-xs font-bold ${
              agentState === 'deep_scan' ? 'text-purple-400' :
              agentState === 'signal_ready' ? 'text-green-400' :
              agentState === 'waiting' ? 'text-yellow-400' :
              'text-zinc-700'
            }`}>
              {agentState === 'deep_scan' ? '🔍 Deep Scan' :
               agentState === 'signal_ready' ? '🎯 Sinal Pronto' :
               agentState === 'waiting' ? '⏳ Aguardando' :
               '🧠 Analisando'}
            </span>
          </div>
        </div>
      </div>
    </>
  );
}
