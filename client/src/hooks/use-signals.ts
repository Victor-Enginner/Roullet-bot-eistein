import { useQuery } from "@tanstack/react-query";
import { api } from "@shared/routes";

export function useSignals() {
  return useQuery({
    queryKey: [api.signals.list.path],
    queryFn: async () => {
      const res = await fetch(api.signals.list.path, { credentials: "include" });
      if (!res.ok) throw new Error("Failed to fetch signals");
      return api.signals.list.responses[200].parse(await res.json());
    },
    refetchInterval: 5000, // Poll every 5s for realtime casino feel
  });
}
