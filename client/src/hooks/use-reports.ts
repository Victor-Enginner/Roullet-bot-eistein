import { useQuery } from "@tanstack/react-query";
import { api } from "@shared/routes";

export function useReport() {
  return useQuery({
    queryKey: [api.reports.get.path],
    queryFn: async () => {
      const res = await fetch(api.reports.get.path, { credentials: "include" });
      if (res.status === 404) return null;
      if (!res.ok) throw new Error("Failed to fetch report");
      return api.reports.get.responses[200].parse(await res.json());
    },
  });
}
