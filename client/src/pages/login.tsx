import { useState, useEffect } from "react";
import { Link, useLocation } from "wouter";
import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Radar, Mail, Lock, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { login, isLoggingIn, user, isLoading } = useAuth();
  const { toast } = useToast();
  const [, setLocation] = useLocation();

  useEffect(() => {
    if (!isLoading && user) {
      setLocation("/");
    }
  }, [user, isLoading, setLocation]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await login({ email, password });
      setLocation("/");
    } catch (error: any) {
      toast({
        title: "Erro no acesso",
        description: error.message || "Email ou senha inválidos",
        variant: "destructive"
      });
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden bg-background">
      {/* Ambient glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-primary/8 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-0 w-[400px] h-[200px] bg-yellow-500/5 rounded-full blur-3xl" />
      </div>

      <Card className="w-full max-w-sm relative z-10 bg-card/80 backdrop-blur-xl border-white/8 shadow-2xl">
        <CardContent className="pt-8 pb-8 px-8">
          {/* Logo */}
          <div className="flex flex-col items-center text-center mb-8">
            <div className="w-16 h-16 rounded-full bg-primary/15 border border-primary/40 flex items-center justify-center mb-4 box-glow-green">
              <Radar className="w-8 h-8 text-primary" />
            </div>
            <h1 className="text-2xl font-display text-white tracking-widest">RADAR DO GREEN</h1>
            <p className="text-xs text-zinc-500 font-medium mt-1 tracking-wider uppercase">Plataforma de Sinais VIP v2.0</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-600" />
              <Input
                type="email"
                placeholder="Seu e-mail"
                className="pl-10 h-11 bg-black/40 border-white/10 focus-visible:ring-primary text-white text-sm"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-600" />
              <Input
                type="password"
                placeholder="Sua senha"
                className="pl-10 h-11 bg-black/40 border-white/10 focus-visible:ring-primary text-white text-sm"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            <Button
              type="submit"
              disabled={isLoggingIn}
              className="w-full h-11 font-bold text-sm bg-primary text-primary-foreground shadow-[0_8px_30px_rgba(34,197,94,0.25)] hover:shadow-[0_8px_40px_rgba(34,197,94,0.4)] transition-all"
            >
              {isLoggingIn ? <Loader2 className="w-5 h-5 animate-spin" /> : "ENTRAR NO RADAR"}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-zinc-600 text-sm">
              Sem conta?{" "}
              <Link href="/register" className="text-primary font-bold hover:underline underline-offset-4">
                Cadastre-se grátis
              </Link>
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
