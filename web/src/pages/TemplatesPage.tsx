import { Link } from "react-router-dom";
import ui from "@/components/ui.module.css";
import { BOOK_TEMPLATES } from "@/lib/templates";
import styles from "./TemplatesPage.module.css";

export function TemplatesPage() {
  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <p className={styles.eyebrow}>Библиотека</p>
        <h1 className={ui.h1}>Шаблоны историй и книг</h1>
        <p className={ui.lead}>
          Каждый шаблон задаёт жанр, тон и стартовые поля. Нажмите «Открыть в
          студии» — форма книги заполнится, вы сможете всё поправить.
        </p>
      </header>

      <div className={styles.grid}>
        {BOOK_TEMPLATES.map((t) => (
          <article key={t.id} className={`${ui.card} ${styles.card}`}>
            <div className={styles.cardTop}>
              <span className={styles.chip}>{t.genre}</span>
              <span className={styles.age}>{t.age}</span>
            </div>
            <h2 className={styles.title}>{t.title}</h2>
            <p className={styles.summary}>{t.summary}</p>
            <dl className={styles.meta}>
              <div>
                <dt>Настроение</dt>
                <dd>{t.mood}</dd>
              </div>
              <div>
                <dt>Страниц по умолчанию</dt>
                <dd>{t.defaultPages}</dd>
              </div>
              <div>
                <dt>Обложка</dt>
                <dd>{t.coverStyle}</dd>
              </div>
            </dl>
            <div className={styles.actions}>
              <Link
                to={`/studio/book?template=${t.id}`}
                className={`${ui.btn} ${ui.btnPrimary}`}
              >
                Открыть в студии
              </Link>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
