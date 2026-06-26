import { Card, CardContent } from "@/components/ui/card";
import { Headset, MessageCircle, BookOpen, Radar, Zap, Shield, Target } from "lucide-react";

export default function SuportePage() {
  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-display text-white tracking-wide flex items-center justify-center gap-3">
          <Headset className="w-8 h-8 text-primary" />
          SUPORTE VIP
        </h1>
        <p className="text-zinc-500 text-sm">Precisando de ajuda ou quer entender a estratégia do RADAR DO GREEN?</p>
      </div>

      {/* How it works */}
      <div className="glass-panel rounded-xl p-6 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent" />
        <div className="relative z-10">
          <h2 className="text-lg font-display text-white mb-4 flex items-center gap-2">
            <Radar className="w-5 h-5 text-primary" />
            COMO O RADAR DO GREEN FUNCIONA
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              {
                icon: Target,
                title: "Análise de Padrões",
                desc: "O algoritmo analisa os últimos 15 resultados, setores da roda e frequência de cores.",
                color: "text-primary",
              },
              {
                icon: Zap,
                title: "Cálculo de Confiança",
                desc: "Cada sinal recebe uma pontuação de 50-96% baseada em múltiplos fatores estatísticos.",
                color: "text-yellow-500",
              },
              {
                icon: Shield,
                title: "Proteção Inteligente",
                desc: "O sistema recomenda gales conforme a confiança: alta = 2 gales, média = 3 gales.",
                color: "text-blue-400",
              }
            ].map(({ icon: Icon, title, desc, color }) => (
              <div key={title} className="bg-black/30 rounded-xl p-4 border border-white/5">
                <Icon className={`w-6 h-6 ${color} mb-3`} />
                <h3 className="text-sm font-bold text-white mb-1">{title}</h3>
                <p className="text-xs text-zinc-500 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Contact cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="glass-panel rounded-xl p-6 flex flex-col items-center text-center">
          <div className="w-14 h-14 rounded-full bg-primary/15 text-primary flex items-center justify-center mb-4 border border-primary/30">
            <MessageCircle className="w-7 h-7" />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">Atendimento Humano</h3>
          <p className="text-zinc-500 text-sm mb-6 leading-relaxed flex-1">
            Fale diretamente com a equipe via WhatsApp para tirar dúvidas sobre a plataforma, pagamentos ou estratégias.
          </p>
          <a
            href="https://wa.me"
            target="_blank"
            rel="noopener noreferrer"
            className="w-full flex items-center justify-center gap-2 h-11 rounded-xl bg-[#25D366]/15 border border-[#25D366]/30 text-[#25D366] font-bold text-sm hover:bg-[#25D366]/25 transition-all"
          >
            <MessageCircle className="w-4 h-4" />
            CHAMAR NO WHATSAPP
          </a>
        </div>

        <div className="glass-panel rounded-xl p-6 flex flex-col items-center text-center">
          <div className="w-14 h-14 rounded-full bg-blue-500/15 text-blue-400 flex items-center justify-center mb-4 border border-blue-500/30">
            <BookOpen className="w-7 h-7" />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">Estratégia Completa</h3>
          <p className="text-zinc-500 text-sm mb-6 leading-relaxed flex-1">
            Acesse o manual completo com todas as estratégias, gestão de banca e como extrair o máximo dos sinais do RADAR.
          </p>
          <a
            href="#"
            target="_blank"
            rel="noopener noreferrer"
            className="w-full flex items-center justify-center gap-2 h-11 rounded-xl border border-blue-500/30 text-blue-400 font-bold text-sm hover:bg-blue-500/10 transition-all"
          >
            <BookOpen className="w-4 h-4" />
            LER MANUAL COMPLETO
          </a>
        </div>
      </div>
    </div>
  );
}
