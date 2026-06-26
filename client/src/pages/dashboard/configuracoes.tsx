import { useState, useEffect } from "react";
import { useAuth } from "@/hooks/use-auth";
import { useUpdateUser } from "@/hooks/use-user";
import { useRadarConfig, useUpdateRadarConfig, useTestTelegram } from "@/hooks/use-radar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Settings, User, Mail, Lock, Loader2, Send, Bot, Shield, Sliders, Volume2, VolumeX } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

export default function ConfiguracoesPage() {
  const { user } = useAuth();
  const updateUser = useUpdateUser();
  const { data: radarCfg } = useRadarConfig();
  const updateRadarConfig = useUpdateRadarConfig();
  const testTelegram = useTestTelegram();
  const { toast } = useToast();

  // Profile form
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // Radar config
  const [telegramToken, setTelegramToken] = useState("");
  const [chatId, setChatId] = useState("");
  const [confidenceThreshold, setConfidenceThreshold] = useState(70);
  const [voiceAlerts, setVoiceAlerts] = useState(true);
  const [signalMode, setSignalMode] = useState("auto");

  useEffect(() => {
    if (user) {
      setName(user.name || "");
      setEmail(user.email || "");
    }
  }, [user]);

  useEffect(() => {
    if (radarCfg) {
      setTelegramToken(radarCfg.telegramToken || "");
      setChatId(radarCfg.chatId || "");
      setConfidenceThreshold(radarCfg.confidenceThreshold);
      setVoiceAlerts(radarCfg.voiceAlerts);
      setSignalMode(radarCfg.signalMode);
    }
  }, [radarCfg]);

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    try {
      const updates: Record<string, string> = { name, email };
      if (password) updates.password = password;
      await updateUser.mutateAsync({ id: user.id, ...updates } as any);
      toast({ title: "Perfil atualizado com sucesso!" });
      setPassword("");
    } catch (error: any) {
      toast({ title: "Erro ao atualizar", description: error.message, variant: "destructive" });
    }
  };

  const handleRadarSave = async () => {
    try {
      await updateRadarConfig.mutateAsync({
        telegramToken,
        chatId,
        confidenceThreshold,
        voiceAlerts,
        signalMode,
      });
      toast({ title: "Configurações do radar salvas!" });
    } catch {
      toast({ title: "Erro ao salvar configurações", variant: "destructive" });
    }
  };

  const handleTestTelegram = () => {
    testTelegram.mutate({ token: telegramToken, chatId });
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-display text-white tracking-wide flex items-center gap-3">
          <Settings className="w-8 h-8 text-primary" />
          CONFIGURAÇÕES
        </h1>
        <p className="text-zinc-500 text-sm font-medium">Gerencie sua conta e as configurações do RADAR DO GREEN</p>
      </div>

      {/* RADAR CONFIG */}
      <div className="glass-panel rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-white/5 bg-black/20 flex items-center gap-3">
          <Bot className="w-5 h-5 text-primary" />
          <h2 className="text-base font-display text-white">RADAR DO GREEN — Motor de Sinais</h2>
        </div>
        <div className="p-6 space-y-5">

          {/* Telegram Token */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-zinc-500 uppercase tracking-wider flex items-center gap-2">
              <Send className="w-3.5 h-3.5" /> Token do Bot Telegram
            </label>
            <Input
              type="password"
              placeholder="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
              className="bg-black/40 border-white/10 focus-visible:ring-primary text-white h-10 text-sm font-mono"
              value={telegramToken}
              onChange={(e) => setTelegramToken(e.target.value)}
            />
          </div>

          {/* Chat ID */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-zinc-500 uppercase tracking-wider">Chat ID</label>
            <div className="flex gap-2">
              <Input
                type="text"
                placeholder="123456789"
                className="bg-black/40 border-white/10 focus-visible:ring-primary text-white h-10 text-sm font-mono"
                value={chatId}
                onChange={(e) => setChatId(e.target.value)}
              />
              <Button
                variant="outline"
                size="sm"
                onClick={handleTestTelegram}
                disabled={testTelegram.isPending || !telegramToken || !chatId}
                className="border-primary/30 text-primary hover:bg-primary/10 whitespace-nowrap h-10"
              >
                {testTelegram.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4 mr-1" />}
                Testar
              </Button>
            </div>
          </div>

          {/* Confidence Threshold */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-zinc-500 uppercase tracking-wider flex items-center justify-between">
              <span className="flex items-center gap-2"><Sliders className="w-3.5 h-3.5" /> Confiança Mínima para Sinal</span>
              <span className="text-primary">{confidenceThreshold}%</span>
            </label>
            <input
              type="range"
              min={50}
              max={95}
              step={5}
              value={confidenceThreshold}
              onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
              className="w-full accent-primary h-1.5 cursor-pointer"
            />
            <div className="flex justify-between text-xs text-zinc-600 font-bold">
              <span>50% (Amplo)</span>
              <span>95% (Preciso)</span>
            </div>
          </div>

          {/* Signal Mode */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-zinc-500 uppercase tracking-wider">Modo de Sinal</label>
            <div className="flex gap-3">
              {['auto', 'manual'].map(mode => (
                <button
                  key={mode}
                  onClick={() => setSignalMode(mode)}
                  className={`flex-1 h-9 rounded-lg border text-xs font-bold uppercase tracking-wider transition-all ${
                    signalMode === mode
                      ? 'bg-primary/15 border-primary/40 text-primary'
                      : 'bg-black/30 border-white/10 text-zinc-500 hover:text-zinc-300'
                  }`}
                >
                  {mode === 'auto' ? 'Automático' : 'Manual'}
                </button>
              ))}
            </div>
          </div>

          {/* Voice Alerts Toggle */}
          <div className="flex items-center justify-between py-3 border-t border-white/5">
            <div className="flex items-center gap-3">
              {voiceAlerts ? <Volume2 className="w-4 h-4 text-primary" /> : <VolumeX className="w-4 h-4 text-zinc-600" />}
              <div>
                <p className="text-sm font-bold text-white">Alertas de Voz</p>
                <p className="text-xs text-zinc-500">Sons ao receber sinais</p>
              </div>
            </div>
            <button
              onClick={() => setVoiceAlerts(!voiceAlerts)}
              className={`w-12 h-6 rounded-full transition-all duration-300 relative ${
                voiceAlerts ? 'bg-primary' : 'bg-zinc-700'
              }`}
            >
              <div className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-all duration-300 ${
                voiceAlerts ? 'left-7' : 'left-1'
              }`} />
            </button>
          </div>

          <Button
            onClick={handleRadarSave}
            disabled={updateRadarConfig.isPending}
            className="w-full h-10 bg-primary/15 border border-primary/30 text-primary hover:bg-primary/25 font-bold text-sm"
          >
            {updateRadarConfig.isPending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Shield className="w-4 h-4 mr-2" />}
            SALVAR CONFIGURAÇÕES DO RADAR
          </Button>
        </div>
      </div>

      {/* PROFILE */}
      <div className="glass-panel rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-white/5 bg-black/20 flex items-center gap-3">
          <User className="w-5 h-5 text-zinc-400" />
          <h2 className="text-base font-display text-white">Dados do Perfil</h2>
        </div>
        <div className="p-6">
          <form onSubmit={handleProfileSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-xs font-bold text-zinc-500 uppercase tracking-wider">Nome Completo</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-600" />
                  <Input
                    type="text"
                    className="pl-9 h-10 bg-black/40 border-white/10 focus-visible:ring-primary text-white text-sm"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                  />
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-xs font-bold text-zinc-500 uppercase tracking-wider">E-mail</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-600" />
                  <Input
                    type="email"
                    className="pl-9 h-10 bg-black/40 border-white/10 focus-visible:ring-primary text-white text-sm"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold text-zinc-500 uppercase tracking-wider">Nova Senha (opcional)</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-600" />
                <Input
                  type="password"
                  placeholder="Deixe em branco para manter"
                  className="pl-9 h-10 bg-black/40 border-white/10 focus-visible:ring-primary text-white text-sm"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </div>
            <div className="pt-2">
              <Button
                type="submit"
                disabled={updateUser.isPending}
                className="h-10 px-8 bg-primary text-primary-foreground font-bold text-sm"
              >
                {updateUser.isPending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                SALVAR PERFIL
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
