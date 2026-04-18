export type SubscriptionTier = "free" | "explorer" | "family" | "atelier";

export type Plan = {
  id: SubscriptionTier;
  name: string;
  tagline: string;
  priceMonthlyRub: number | null;
  tokensMonthly: number;
  perks: string[];
  highlighted?: boolean;
};

export const PLANS: Plan[] = [
  {
    id: "free",
    name: "Пробный",
    tagline: "Познакомиться со студией",
    priceMonthlyRub: 0,
    tokensMonthly: 400,
    perks: [
      "До 3 проектов в облаке",
      "Водяной знак на экспорте",
      "Базовые шаблоны историй",
    ],
  },
  {
    id: "explorer",
    name: "Исследователь",
    tagline: "Для первых семейных книг",
    priceMonthlyRub: 690,
    tokensMonthly: 3200,
    perks: [
      "20 проектов",
      "Без водяного знака",
      "Все шаблоны + кастом обложки",
      "Приоритет очереди генерации",
    ],
    highlighted: true,
  },
  {
    id: "family",
    name: "Семья",
    tagline: "Несколько детей и альбомы",
    priceMonthlyRub: 1290,
    tokensMonthly: 7200,
    perks: [
      "Безлимит проектов",
      "Пакет «видео + книга» со скидкой токенов",
      "Общий семейный архив",
      "Ранний доступ к новым моделям",
    ],
  },
  {
    id: "atelier",
    name: "Ателье",
    tagline: "Подарки и малый бизнес",
    priceMonthlyRub: 3490,
    tokensMonthly: 22000,
    perks: [
      "Коммерческая лицензия на печать",
      "API webhooks (когда подключите backend)",
      "Персональный менеджер",
      "White-label экспорт PDF",
    ],
  },
];

export function tokensForTier(tier: SubscriptionTier): number {
  const p = PLANS.find((x) => x.id === tier);
  return p?.tokensMonthly ?? 400;
}
