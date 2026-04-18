/**
 * Заглушки под будущий backend (FastAPI / Node).
 * Замените fetch на реальные эндпоинты, например:
 *   POST /api/v1/jobs/book
 *   GET  /api/v1/jobs/:id
 */

export type BookJobPayload = {
  title: string;
  genre: string;
  ageRange: string;
  pageCount: number;
  heroName: string;
  heroTraits: string;
  synopsis: string;
  coverBrief: string;
  illustrationStyle: string;
  photoRefs: string[];
  templateId?: string;
};

export type GenerationJob = {
  id: string;
  status: "queued" | "running" | "done" | "error";
  kind: "image" | "video" | "story" | "book";
  createdAt: string;
  tokenEstimate: number;
  message?: string;
};

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function enqueueBookJob(
  payload: BookJobPayload,
  tokenEstimate: number
): Promise<GenerationJob> {
  await delay(400);
  console.info("[api stub] enqueueBookJob", { payload, tokenEstimate });
  return {
    id: `job_${Math.random().toString(36).slice(2, 10)}`,
    status: "queued",
    kind: "book",
    createdAt: new Date().toISOString(),
    tokenEstimate,
    message: "Backend не подключён — задача сохранена только в консоли.",
  };
}

export async function enqueueImageJob(formData: FormData): Promise<GenerationJob> {
  await delay(350);
  console.info("[api stub] enqueueImageJob", [...formData.keys()]);
  return {
    id: `img_${Math.random().toString(36).slice(2, 10)}`,
    status: "queued",
    kind: "image",
    createdAt: new Date().toISOString(),
    tokenEstimate: Number(formData.get("tokenEstimate")) || 0,
  };
}

export async function enqueueVideoJob(formData: FormData): Promise<GenerationJob> {
  await delay(350);
  console.info("[api stub] enqueueVideoJob", [...formData.keys()]);
  return {
    id: `vid_${Math.random().toString(36).slice(2, 10)}`,
    status: "queued",
    kind: "video",
    createdAt: new Date().toISOString(),
    tokenEstimate: Number(formData.get("tokenEstimate")) || 0,
  };
}

export async function enqueueStoryJob(body: {
  synopsis: string;
  tokenEstimate: number;
}): Promise<GenerationJob> {
  await delay(300);
  console.info("[api stub] enqueueStoryJob", body);
  return {
    id: `stry_${Math.random().toString(36).slice(2, 10)}`,
    status: "queued",
    kind: "story",
    createdAt: new Date().toISOString(),
    tokenEstimate: body.tokenEstimate,
  };
}
