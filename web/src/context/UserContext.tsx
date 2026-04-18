import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { SubscriptionTier } from "@/lib/subscriptions";

export type UserState = {
  balanceTokens: number;
  tier: SubscriptionTier;
};

const initial: UserState = {
  balanceTokens: 2400,
  tier: "explorer",
};

type UserContextValue = UserState & {
  setBalance: (n: number) => void;
  setTier: (t: SubscriptionTier) => void;
  spendTokens: (amount: number) => boolean;
};

const UserContext = createContext<UserContextValue | null>(null);

export function UserProvider({ children }: { children: ReactNode }) {
  const [balanceTokens, setBalanceTokens] = useState(initial.balanceTokens);
  const [tier, setTier] = useState<SubscriptionTier>(initial.tier);

  const spendTokens = useCallback((amount: number) => {
    if (amount <= 0) return true;
    if (balanceTokens < amount) return false;
    setBalanceTokens((b) => b - amount);
    return true;
  }, [balanceTokens]);

  const value = useMemo(
    () => ({
      balanceTokens,
      tier,
      setBalance: setBalanceTokens,
      setTier,
      spendTokens,
    }),
    [balanceTokens, tier, spendTokens]
  );

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
}

export function useUser() {
  const ctx = useContext(UserContext);
  if (!ctx) throw new Error("useUser must be inside UserProvider");
  return ctx;
}
