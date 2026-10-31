import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, getToken, setToken } from "./api";
import type { UserBrief } from "./types";

interface Session {
  user: UserBrief | null;
  ready: boolean;
  signIn: (userId: number) => Promise<UserBrief>;
  signOut: () => void;
}

const Ctx = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const [user, setUser] = useState<UserBrief | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      setReady(true);
      return;
    }
    api<UserBrief>("/api/me")
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setReady(true));
  }, []);

  const signIn = async (userId: number) => {
    const res = await api<{ token: string; user: UserBrief }>("/api/auth/demo-login", { method: "POST", json: { user_id: userId } });
    setToken(res.token);
    qc.clear();
    setUser(res.user);
    return res.user;
  };
  const signOut = () => {
    setToken(null);
    qc.clear();
    setUser(null);
  };
  return <Ctx.Provider value={{ user, ready, signIn, signOut }}>{children}</Ctx.Provider>;
}

export function useSession() {
  const s = useContext(Ctx);
  if (!s) throw new Error("useSession outside SessionProvider");
  return s;
}
