/**
 * Стоимость операций в токенах Bok.
 * Подключите backend: POST /api/billing/estimate и списание по job_id.
 */
export const TOKEN_COSTS = {
  /** Одно сгенерированное изображение (обложка / иллюстрация страницы) */
  imagePerUnit: 180,
  /** Редактирование или апскейл загруженного фото */
  imageEditPerUnit: 220,
  /** Секунда видео (базовая модель) */
  videoPerSecond: 95,
  /** Генерация текста: база + за 1k символов выхода */
  storyBase: 120,
  storyPer1kChars: 35,
  /** Полная книга: база + за страницу (текст + макет) */
  bookBase: 280,
  bookPerPage: 45,
  /** Озвучка: за минуту */
  ttsPerMinute: 160,
} as const;

export function estimateStoryTokens(estimatedChars: number) {
  const k = Math.max(0, estimatedChars) / 1000;
  return Math.ceil(TOKEN_COSTS.storyBase + k * TOKEN_COSTS.storyPer1kChars);
}

export function estimateBookTokens(pageCount: number, withCover: boolean) {
  const pages = Math.max(4, Math.min(64, pageCount));
  const cover = withCover ? TOKEN_COSTS.imagePerUnit : 0;
  return Math.ceil(
    TOKEN_COSTS.bookBase + pages * TOKEN_COSTS.bookPerPage + cover
  );
}

export function estimateVideoTokens(seconds: number) {
  const s = Math.max(2, Math.min(120, seconds));
  return Math.ceil(s * TOKEN_COSTS.videoPerSecond);
}

export function estimateImageBatchTokens(count: number, isEdit: boolean) {
  const unit = isEdit ? TOKEN_COSTS.imageEditPerUnit : TOKEN_COSTS.imagePerUnit;
  return Math.ceil(Math.max(1, count) * unit);
}
