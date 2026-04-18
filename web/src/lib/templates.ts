export type StoryTemplate = {
  id: string;
  title: string;
  genre: string;
  age: string;
  summary: string;
  defaultHero: string;
  defaultPages: number;
  mood: string;
};

export type BookTemplate = StoryTemplate & {
  coverStyle: string;
  illustrationStyle: string;
};

export const STORY_TEMPLATES: StoryTemplate[] = [
  {
    id: "star-journey",
    title: "Звёздное путешествие",
    genre: "Фантастика",
    age: "6–9 лет",
    summary:
      "Ребёнок находит волшебный компас и летит спасать планету дружбы от серых туч скуки.",
    defaultHero: "Алекс",
    defaultPages: 12,
    mood: "Тёплый, смешной, с мягким финалом",
  },
  {
    id: "forest-secret",
    title: "Тайна лесного ручья",
    genre: "Приключение",
    age: "5–8 лет",
    summary:
      "Герой следует по следам светлячков и узнаёт, почему в лесу пропал звук воды.",
    defaultHero: "Мира",
    defaultPages: 10,
    mood: "Уютная сказка с загадкой",
  },
  {
    id: "grandma-recipe",
    title: "Рецепт бабушки",
    genre: "Семейная история",
    age: "7–12 лет",
    summary:
      "История о том, как семейный рецепт оживает и сводит поколения за одним столом.",
    defaultHero: "Тимур",
    defaultPages: 14,
    mood: "Ностальгия, юмор, еда",
  },
  {
    id: "dino-school",
    title: "Школа динозавров",
    genre: "Юмор",
    age: "4–7 лет",
    summary:
      "Маленький герой попадает в школу, где учатся не страшить, а дружить.",
    defaultHero: "Соня",
    defaultPages: 8,
    mood: "Ярко, короткие сцены, много смеха",
  },
];

export const BOOK_TEMPLATES: BookTemplate[] = STORY_TEMPLATES.map((s) => ({
  ...s,
  coverStyle: "Мягкая акварель, крупный герой, много воздуха",
  illustrationStyle: "Плоские иллюстрации с тёплой палитрой",
}));

export function getTemplateById(id: string): StoryTemplate | undefined {
  return STORY_TEMPLATES.find((t) => t.id === id);
}
