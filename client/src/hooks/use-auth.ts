import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@shared/routes";
import { type User } from "@shared/schema";
import { z } from "zod";

// Safe user type without password
export type SafeUser = Omit<User, "password">;

async function parseErrorMessage(res: Response, fallback: string): Promise<string> {
  try {
    const body = await res.json();
    return body?.message || fallback;
  } catch {
    return fallback;
  }
}

export function useAuth() {
  const queryClient = useQueryClient();

  const { data: user, isLoading, error } = useQuery<SafeUser | null>({
    queryKey: [api.auth.me.path],
    queryFn: async () => {
      const res = await fetch(api.auth.me.path, { credentials: "include" });
      if (res.status === 401) return null;
      if (!res.ok) throw new Error("Falha ao verificar autenticação");
      const data = await res.json();
      const { password: _p, ...safeUser } = data;
      return safeUser as SafeUser;
    },
    retry: false,
  });

  const loginMutation = useMutation({
    mutationFn: async (credentials: z.infer<typeof api.auth.login.input>) => {
      const res = await fetch(api.auth.login.path, {
        method: api.auth.login.method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(credentials),
        credentials: "include",
      });

      if (!res.ok) {
        const msg =
          res.status === 401
            ? "Email ou senha incorretos"
            : res.status === 400
            ? await parseErrorMessage(res, "Dados inválidos")
            : res.status >= 500
            ? "Erro no servidor. Tente novamente em instantes."
            : await parseErrorMessage(res, "Falha ao entrar");
        throw new Error(msg);
      }

      const data = await res.json();
      const { password: _p, ...safeUser } = data;
      return safeUser as SafeUser;
    },
    onSuccess: (data) => {
      queryClient.setQueryData([api.auth.me.path], data);
    },
  });

  const registerMutation = useMutation({
    mutationFn: async (data: z.infer<typeof api.auth.register.input>) => {
      const res = await fetch(api.auth.register.path, {
        method: api.auth.register.method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
        credentials: "include",
      });

      if (!res.ok) {
        const msg =
          res.status === 400
            ? await parseErrorMessage(res, "Dados de cadastro inválidos")
            : res.status === 409
            ? "Este email já está cadastrado"
            : res.status >= 500
            ? "Erro no servidor. Tente novamente em instantes."
            : await parseErrorMessage(res, "Falha ao cadastrar");
        throw new Error(msg);
      }

      const body = await res.json();
      const { password: _p, ...safeUser } = body;
      return safeUser as SafeUser;
    },
    onSuccess: (data) => {
      queryClient.setQueryData([api.auth.me.path], data);
    },
  });

  const logoutMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(api.auth.logout.path, {
        method: api.auth.logout.method,
        credentials: "include",
      });
      if (!res.ok) throw new Error("Falha ao sair");
    },
    onSuccess: () => {
      queryClient.setQueryData([api.auth.me.path], null);
      queryClient.clear();
    },
  });

  return {
    user,
    isLoading,
    error,
    login: loginMutation.mutateAsync,
    register: registerMutation.mutateAsync,
    logout: logoutMutation.mutateAsync,
    isLoggingIn: loginMutation.isPending,
    isRegistering: registerMutation.isPending,
    isLoggingOut: logoutMutation.isPending,
  };
}
