import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import ui from "@/components/ui.module.css";
import { TOKEN_COSTS, estimateVideoTokens } from "@/lib/tokens";
import { enqueueVideoJob } from "@/lib/api";
import { useUser } from "@/context/UserContext";
import styles from "./StudioPages.module.css";

export function VideoStudioPage() {
  const { balanceTokens, spendTokens } = useUser();
  const [seconds, setSeconds] = useState(8);
  const [script, setScript] = useState(
    "Герой машет рукой из волшебного поезда, мягкий закат, частицы света"
  );
  const [status, setStatus] = useState<string | null>(null);

  const cost = useMemo(() => estimateVideoTokens(seconds), [seconds]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (balanceTokens < cost) {
      setStatus("Недостаточно токенов.");
      return;
    }
    const fd = new FormData();
    fd.set("seconds", String(seconds));
    fd.set("script", script);
    fd.set("tokenEstimate", String(cost));
    const job = await enqueueVideoJob(fd);
    if (spendTokens(cost)) {
      setStatus(
        `Видео-задача ${job.id} (−${cost} ток.). Оценка: ${seconds} с × ${TOKEN_COSTS.videoPerSecond} ток/с.`
      );
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <p className={styles.eyebrow}>Студия · Видео</p>
        <h1 className={ui.h1}>Короткое семейное видео</h1>
        <p className={ui.lead}>
          Опишите сцену и длительность. Интеграция с video-моделью — на стороне
          backend; здесь — UX и расчёт стоимости по секундам.
        </p>
      </header>

      <div className={styles.split}>
        <form className={`${ui.card} ${styles.form}`} onSubmit={onSubmit}>
          <label className={styles.field}>
            <span className={ui.label}>Длительность (сек.)</span>
            <input
              className={ui.input}
              type="range"
              min={2}
              max={60}
              value={seconds}
              onChange={(e) => setSeconds(Number(e.target.value))}
            />
            <div className={styles.rangeVal}>{seconds} секунд</div>
          </label>

          <label className={styles.field}>
            <span className={ui.label}>Сценарий / движение камеры</span>
            <textarea
              className={ui.textarea}
              value={script}
              onChange={(e) => setScript(e.target.value)}
            />
          </label>

          <label className={styles.field}>
            <span className={ui.label}>Референсное фото (опционально)</span>
            <label className={ui.dropzone}>
              <input type="file" accept="image/*" />
              Пока только UI — файл уйдёт в multipart на backend
            </label>
          </label>

          <div className={styles.footerRow}>
            <div>
              <span className={ui.pill}>оценка</span>
              <span className={ui.cost}> {cost} токенов</span>
            </div>
            <button type="submit" className={`${ui.btn} ${ui.btnPrimary}`}>
              Запланировать ролик
            </button>
          </div>
          {status && <p className={styles.notice}>{status}</p>}
        </form>

        <aside className={`${ui.card} ${styles.side}`}>
          <h2 className={styles.sideTitle}>Тарификация видео</h2>
          <p className={styles.sideP}>
            Базовая формула: длительность × {TOKEN_COSTS.videoPerSecond}{" "}
            токенов/сек (настраивается на сервере под модель).
          </p>
          <p className={styles.sideP}>
            Для семейного тарифа можно задать скидочный множитель на связку
            «книга + ролик» — поле готово в конфиге подписок.
          </p>
        </aside>
      </div>
    </div>
  );
}
