import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import ui from "@/components/ui.module.css";
import { estimateBookTokens, estimateStoryTokens } from "@/lib/tokens";
import { enqueueBookJob } from "@/lib/api";
import { getTemplateById } from "@/lib/templates";
import { useUser } from "@/context/UserContext";
import styles from "./StudioPages.module.css";

const GENRES = [
  "Сказка",
  "Приключение",
  "Фантастика",
  "Повседневность",
  "Юмор",
  "Семейная история",
];

const AGES = ["3–5 лет", "5–8 лет", "6–10 лет", "8–12 лет", "Семейное чтение"];

export function BookStudioPage() {
  const [params] = useSearchParams();
  const templateId = params.get("template") ?? undefined;
  const preset = templateId ? getTemplateById(templateId) : undefined;

  const { balanceTokens, spendTokens } = useUser();

  const [title, setTitle] = useState(preset?.title ?? "Моя первая книга");
  const [genre, setGenre] = useState(preset?.genre ?? "Сказка");
  const [ageRange, setAgeRange] = useState(preset?.age ?? "5–8 лет");
  const [pageCount, setPageCount] = useState(preset?.defaultPages ?? 12);
  const [heroName, setHeroName] = useState(preset?.defaultHero ?? "");
  const [heroTraits, setHeroTraits] = useState("добрый, любопытный, немного стеснительный");
  const [synopsis, setSynopsis] = useState(
    preset?.summary ??
      "Коротко: о чём история, какой конфликт, чему учит финал."
  );
  const [coverBrief, setCoverBrief] = useState(
    "Крупный герой на обложке, тёплые цвета, много воздуха, без страшных деталей"
  );
  const [illustrationStyle, setIllustrationStyle] = useState(
    "Акварель, мягкие контуры, светлый фон"
  );
  const [withCover, setWithCover] = useState(true);
  const [photos, setPhotos] = useState<File[]>([]);
  const [status, setStatus] = useState<string | null>(null);

  const storyEstimateChars = useMemo(
    () => Math.min(12000, 400 + pageCount * 650),
    [pageCount]
  );

  const bookCost = useMemo(
    () => estimateBookTokens(pageCount, withCover),
    [pageCount, withCover]
  );

  const storyOnlyCost = useMemo(
    () => estimateStoryTokens(storyEstimateChars),
    [storyEstimateChars]
  );

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (balanceTokens < bookCost) {
      setStatus("Недостаточно токенов для книги.");
      return;
    }
    const job = await enqueueBookJob(
      {
        title,
        genre,
        ageRange,
        pageCount,
        heroName,
        heroTraits,
        synopsis,
        coverBrief,
        illustrationStyle,
        photoRefs: photos.map((f) => f.name),
        templateId,
      },
      bookCost
    );
    if (spendTokens(bookCost)) {
      setStatus(
        `Книга в очереди: ${job.id}. Списано ${bookCost} ток. (текст ≈ ${storyOnlyCost} ток. отдельной оценкой истории)`
      );
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <p className={styles.eyebrow}>Студия · Книга</p>
        <h1 className={ui.h1}>Параметры книги и обложки</h1>
        <p className={ui.lead}>
          Задайте жанр, героя, число страниц и визуальный стиль. Фотографии
          пойдут в pipeline обезличивания и иллюстраций — после подключения API.
        </p>
        {preset && (
          <p className={styles.presetBanner}>
            Шаблон: <strong>{preset.title}</strong> — поля можно менять свободно.
          </p>
        )}
      </header>

      <form className={`${ui.card} ${styles.bookForm}`} onSubmit={onSubmit}>
        <div className={styles.bookGrid}>
          <label className={styles.field}>
            <span className={ui.label}>Название книги</span>
            <input
              className={ui.input}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
          </label>

          <label className={styles.field}>
            <span className={ui.label}>Жанр</span>
            <select
              className={ui.select}
              value={genre}
              onChange={(e) => setGenre(e.target.value)}
            >
              {GENRES.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          </label>

          <label className={styles.field}>
            <span className={ui.label}>Возраст читателя</span>
            <select
              className={ui.select}
              value={ageRange}
              onChange={(e) => setAgeRange(e.target.value)}
            >
              {AGES.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
          </label>

          <label className={styles.field}>
            <span className={ui.label}>Страниц (4–64)</span>
            <input
              className={ui.input}
              type="number"
              min={4}
              max={64}
              value={pageCount}
              onChange={(e) => setPageCount(Number(e.target.value))}
            />
          </label>

          <label className={styles.field}>
            <span className={ui.label}>Главный герой</span>
            <input
              className={ui.input}
              value={heroName}
              onChange={(e) => setHeroName(e.target.value)}
              placeholder="Имя ребёнка или вымышленное"
            />
          </label>

          <label className={styles.field}>
            <span className={ui.label}>Черты характера</span>
            <input
              className={ui.input}
              value={heroTraits}
              onChange={(e) => setHeroTraits(e.target.value)}
            />
          </label>
        </div>

        <label className={styles.field}>
          <span className={ui.label}>Содержание / синопсис</span>
          <textarea
            className={ui.textarea}
            value={synopsis}
            onChange={(e) => setSynopsis(e.target.value)}
            rows={5}
          />
        </label>

        <div className={ui.grid2}>
          <label className={styles.field}>
            <span className={ui.label}>Обложка — бриф художнику</span>
            <textarea
              className={ui.textarea}
              value={coverBrief}
              onChange={(e) => setCoverBrief(e.target.value)}
              rows={4}
            />
          </label>
          <label className={styles.field}>
            <span className={ui.label}>Стиль иллюстраций</span>
            <textarea
              className={ui.textarea}
              value={illustrationStyle}
              onChange={(e) => setIllustrationStyle(e.target.value)}
              rows={4}
            />
          </label>
        </div>

        <label className={styles.field}>
          <span className={ui.label}>Фото для узнаваемости героя</span>
          <label className={ui.dropzone}>
            <input
              type="file"
              accept="image/*"
              multiple
              onChange={(e) =>
                setPhotos(e.target.files ? Array.from(e.target.files) : [])
              }
            />
            {photos.length
              ? `Файлов: ${photos.length} (имена уйдут в job payload)`
              : "Загрузите 1–5 фото — на backend позже добавится privacy-pipeline"}
          </label>
        </label>

        <label className={`${styles.field} ${styles.checkRow}`}>
          <span className={ui.label}>Генерация обложки</span>
          <label className={styles.switch}>
            <input
              type="checkbox"
              checked={withCover}
              onChange={(e) => setWithCover(e.target.checked)}
            />
            <span>Включить отдельную генерацию обложки (+ токены к оценке)</span>
          </label>
        </label>

        <div className={styles.metrics}>
          <div>
            <span className={ui.pill}>книга</span>
            <span className={ui.cost}> {bookCost} токенов</span>
            <span className={styles.balanceHint}>
              {" "}
              · прогноз текста ~{storyEstimateChars} зн. → история ≈{" "}
              {storyOnlyCost} ток.
            </span>
          </div>
          <div className={styles.balanceHint}>
            Баланс: {balanceTokens.toLocaleString("ru-RU")}
          </div>
        </div>

        <div className={styles.footerRow}>
          <button type="submit" className={`${ui.btn} ${ui.btnPrimary}`}>
            Сгенерировать книгу (демо)
          </button>
        </div>
        {status && <p className={styles.notice}>{status}</p>}
      </form>
    </div>
  );
}
