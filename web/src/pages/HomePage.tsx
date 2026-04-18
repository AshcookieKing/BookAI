import type { CSSProperties } from "react";
import { Link } from "react-router-dom";
import ui from "@/components/ui.module.css";
import styles from "./HomePage.module.css";

const tiles = [
  {
    to: "/studio/photo",
    title: "Фото",
    desc: "Загрузите снимок — получите иллюстрации в едином стиле для книги.",
    tag: "Изображения",
    gradient: "linear-gradient(145deg, rgba(245,183,58,0.35), rgba(124,58,237,0.2))",
  },
  {
    to: "/studio/video",
    title: "Видео",
    desc: "Короткий ролик по сценарию: герой, декорации, настроение.",
    tag: "Движение",
    gradient: "linear-gradient(145deg, rgba(251,113,133,0.35), rgba(124,58,237,0.2))",
  },
  {
    to: "/studio/book",
    title: "Книга",
    desc: "Параметры сюжета, обложка, число страниц — готовый макет истории.",
    tag: "Сборка",
    gradient: "linear-gradient(145deg, rgba(167,139,250,0.4), rgba(245,183,58,0.15))",
  },
];

export function HomePage() {
  return (
    <div className={styles.wrap}>
      <section className={styles.hero}>
        <p className={styles.kicker}>Персональные книги для семьи</p>
        <h1 className={ui.h1}>
          Создавайте истории,{" "}
          <span className={styles.grad}>в которых живут ваши фото</span>
        </h1>
        <p className={ui.lead}>
          Bok Studio — веб-студия в духе современных AI-продуктов: тёмная
          сцена, мягкий свет, понятные шаги. Пока без backend: интерфейс и
          расчёт токенов готовы к подключению моделей.
        </p>
        <div className={styles.heroCtas}>
          <Link to="/studio/book" className={`${ui.btn} ${ui.btnPrimary}`}>
            Собрать книгу
          </Link>
          <Link to="/templates" className={`${ui.btn} ${ui.btnGhost}`}>
            Шаблоны сюжетов
          </Link>
        </div>
      </section>

      <section className={styles.tiles} aria-label="Направления студии">
        {tiles.map((t) => (
          <Link
            key={t.to}
            to={t.to}
            className={styles.tile}
            style={{ "--tile-bg": t.gradient } as CSSProperties}
          >
            <span className={styles.tileTag}>{t.tag}</span>
            <h2 className={styles.tileTitle}>{t.title}</h2>
            <p className={styles.tileDesc}>{t.desc}</p>
            <span className={styles.tileArrow}>→</span>
          </Link>
        ))}
      </section>

      <section className={`${ui.card} ${styles.band}`}>
        <div>
          <h2 className={styles.bandTitle}>Токены и подписки</h2>
          <p className={styles.bandText}>
            Каждая операция имеет оценку в токенах: фото, секунды видео, объём
            текста книги. Планы пополняют баланс и открывают функции экспорта.
          </p>
        </div>
        <Link to="/pricing" className={`${ui.btn} ${ui.btnGhost}`}>
          Смотреть тарифы
        </Link>
      </section>
    </div>
  );
}
