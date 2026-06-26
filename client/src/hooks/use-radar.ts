import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@shared/routes";
import { useToast } from "@/hooks/use-toast";

export function useHealth() {
  return useQuery({
    queryKey: [api.health.get.path],
    queryFn: async () => {
      try {
        const res = await fetch(api.health.get.path);
        if (!res.ok) throw new Error("offline");
        return await res.json() as { status: string; system: string; version: string; radarActive: boolean; timestamp: string };
      } catch {
        return null; // null = offline
      }
    },
    refetchInterval: 5000,
    retry: false,
    staleTime: 3000,
  });
}

export function useRadarConfig() {
  return useQuery({
    queryKey: [api.radar.getConfig.path],
    queryFn: async () => {
      const res = await fetch(api.radar.getConfig.path, { credentials: "include" });
      if (!res.ok) throw new Error("Failed to fetch config");
      return await res.json() as {
        id: number;
        telegramToken: string;
        chatId: string;
        signalMode: string;
        confidenceThreshold: number;
        voiceAlerts: boolean;
        radarActive: boolean;
      };
    },
  });
}

export function useUpdateRadarConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (updates: Record<string, unknown>) => {
      const res = await fetch(api.radar.updateConfig.path, {
        method: api.radar.updateConfig.method,
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(updates),
      });
      if (!res.ok) throw new Error("Failed to update config");
      return await res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [api.radar.getConfig.path] });
      queryClient.invalidateQueries({ queryKey: [api.health.get.path] });
    },
  });
}

export function useStartRadar() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  return useMutation({
    mutationFn: async () => {
      const res = await fetch(api.radar.start.path, {
        method: api.radar.start.method,
        credentials: "include",
      });
      return await res.json() as { success: boolean; message: string };
    },
    onSuccess: (data) => {
      toast({ title: data.message, variant: "default" });
      queryClient.invalidateQueries({ queryKey: [api.radar.getConfig.path] });
      queryClient.invalidateQueries({ queryKey: [api.health.get.path] });
      queryClient.invalidateQueries({ queryKey: [api.signals.list.path] });
    },
    onError: () => {
      toast({ title: "Erro ao ativar radar", variant: "destructive" });
    }
  });
}

export function useStopRadar() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  return useMutation({
    mutationFn: async () => {
      const res = await fetch(api.radar.stop.path, {
        method: api.radar.stop.method,
        credentials: "include",
      });
      return await res.json() as { success: boolean; message: string };
    },
    onSuccess: () => {
      toast({ title: "Radar desativado", variant: "default" });
      queryClient.invalidateQueries({ queryKey: [api.radar.getConfig.path] });
      queryClient.invalidateQueries({ queryKey: [api.health.get.path] });
    },
  });
}

export function useTestTelegram() {
  const { toast } = useToast();
  return useMutation({
    mutationFn: async (data: { token?: string; chatId?: string }) => {
      const res = await fetch(api.radar.testTelegram.path, {
        method: api.radar.testTelegram.method,
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(data),
      });
      return await res.json() as { success: boolean; message: string };
    },
    onSuccess: (data) => {
      if (data.success) {
        toast({ title: "Telegram conectado!", description: data.message });
      } else {
        toast({ title: "Falha no Telegram", description: data.message, variant: "destructive" });
      }
    },
  });
}

export function useGenerateSignal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await fetch(api.signals.generate.path, {
        method: api.signals.generate.method,
        credentials: "include",
      });
      if (!res.ok) throw new Error("Failed to generate signal");
      return await res.json() as {
        entry: string;
        targetColor: string;
        confidence: number;
        protection: string;
        countdown: number;
        timestamp: string;
      };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [api.signals.list.path] });
    }
  });
}
