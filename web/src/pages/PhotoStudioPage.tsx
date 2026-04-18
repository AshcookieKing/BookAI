import { useMemo, useState, type FormEvent } from "react";
import ui from "@/components/ui.module.css";
import { TOKEN_COSTS, estimateImageBatchTokens } from "@/lib/tokens";
import { enqueueImageJob } from "@/lib/api";
import { useUser } from "@/context/UserContext";
import styles from "./StudioPages.module.css";

export function PhotoStudioPage() {
  const { balanceTokens, spendTokens } = useUser();
  const [files, setFiles] = useState<File[]>([]);
  const [prompt, setPrompt] = useState(
    "Детская книжная иллюстрация, мягкий свет, пастель, герой похож на фото"
  );
  const [editMode, setEditMode] = useState(false);
  const [count, setCount] = useState(1);
  const [status, setStatus] = useState<string | null>(null);

  const cost = useMemo(
    () => estimateImageBatchTokens(count, editMode),
    [count, editMode]
  );

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (balanceTokens < cost) {
      setStatus("Недостаточно токенов. Откройте раздел «Подписки».");
      return;
    }
    const fd = new FormData();
    fd.set("prompt", prompt);
    fd.set("count", String(count));
    fd.set("editMode", editMode ? "1" : "0");
    fd.set("tokenEstimate", String(cost));
    files.forEach((f) => fd.append("photos", f));
    const job = await enqueueImageJob(fd);
    if (spendTokens(cost)) {
      setStatus(
        `Задача ${job.id} поставлена в очередь (−${cost} ток.). Backend пока заглушка — см. консоль.`
      );
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <p className={styles.eyebrow}>Студия · Фото</p>
        <h1 className={ui.h1}>Иллюстрации по вашим снимкам</h1>
        <p className={ui.lead}>
          Загрузите референсы — позже backend передаст их в vision-модель и
          генератор изображений. Сейчас интерфейс считает токены и создаёт
          заглушку задачи.
        </p>
      </header>

      <div className={styles.split}>
        <form className={`${ui.card} ${styles.form}`} onSubmit={onSubmit}>
          <label className={styles.field}>
            <span className={ui.label}>Референсные фото</span>
            <label className={ui.dropzone}>
              <input
                type="file"
                accept="image/*"
                multiple
                onChange={(e) =>
                  setFiles(e.target.files ? Array.from(e.target.files) : [])
                }
              />
              {files.length
                ? `Выбрано файлов: ${files.length}`
                : "Перетащите или нажмите — JPG, PNG, WebP"}
            </label>
          </label>

          <label className={styles.field}>
            <span className={ui.label}>Промпт / стиль</span>
            <textarea
              className={ui.textarea}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />
          </label>

          <div className={ui.grid2}>
            <label className={styles.field}>
              <span className={ui.label}>Вариантов</span>
              <input
                className={ui.input}
                type="number"
                min={1}
                max={8}
                value={count}
                onChange={(e) => setCount(Number(e.target.value))}
              />
            </label>
            <label className={`${styles.field} ${styles.checkRow}`}>
              <span className={ui.label}>Режим</span>
              <label className={styles.switch}>
                <input
                  type="checkbox"
                  checked={editMode}
                  onChange={(e) => setEditMode(e.target.checked)}
                />
                <span>
                  Редактирование загрузки (+{TOKEN_COSTS.imageEditPerUnit - TOKEN_COSTS.imagePerUnit}{" "}
                  ток. к единице)
                </span>
              </label>
            </label>
          </div>

          <div className={styles.footerRow}>
            <div>
              <span className={ui.pill}>оценка</span>
              <span className={ui.cost}> {cost} токенов</span>
              <span className={styles.balanceHint}>
                {" "}
                · баланс {balanceTokens.toLocaleString("ru-RU")}
              </span>
            </div>
            <button type="submit" className={`${ui.btn} ${ui.btnPrimary}`}>
              Поставить в очередь
            </button>
          </div>
          {status && <p className={styles.notice}>{status}</p>}
        </form>

        <aside className={`${ui.card} ${styles.side}`}>
          <h2 className={styles.sideTitle}>Как это сойдётся с backend</h2>
          <ul className={styles.list}>
            <li>
              <code>POST /api/v1/jobs/image</code> — multipart: файлы + промпт.
            </li>
            <li>
              Ответ: <code>job_id</code>, списание токенов после успеха воркера.
            </li>
            <li>Базовая цена за кадр: {TOKEN_COSTS.imagePerUnit} ток.</li>
          </ul>
        </aside>
      </div>
    </div>
  );
}
