import { useQuery } from "@tanstack/react-query";
import { api } from "@shared/routes";

export function useMetrics() {
  return useQuery({
    queryKey: [api.metrics.get.path],
    queryFn: async () => {
      const res = await fetch(api.metrics.get.path, { credentials: "include" });
      if (!res.ok) throw new Error("Failed to fetch metrics");
      return await res.json() as {
        signalsToday: number;
        winRate: number;
        currentStreak: number;
        lastSignalResult: string;
        totalGreens: number;
        totalReds: number;
        lastNumber: number;
      };
    },
    refetchInterval: 10000,
  });
}
