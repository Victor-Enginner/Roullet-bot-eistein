import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, buildUrl } from "@shared/routes";
import { z } from "zod";

export function useUpdateUser() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ id, ...data }: { id: number } & Partial<z.infer<typeof api.users.update.input>>) => {
      const url = buildUrl(api.users.update.path, { id });
      const res = await fetch(url, {
        method: api.users.update.method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
        credentials: "include",
      });
      
      if (!res.ok) {
        if (res.status === 400) throw new Error("Validation failed");
        if (res.status === 404) throw new Error("User not found");
        throw new Error("Failed to update profile");
      }
      
      return api.users.update.responses[200].parse(await res.json());
    },
    onSuccess: (updatedUser) => {
      queryClient.setQueryData([api.auth.me.path], updatedUser);
    }
  });
}
