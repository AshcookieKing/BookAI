import { Link, NavLink, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import { useUser } from "@/context/UserContext";
import styles from "./Layout.module.css";

const nav = [
  { to: "/studio/photo", label: "Фото" },
  { to: "/studio/video", label: "Видео" },
  { to: "/studio/book", label: "Книга" },
  { to: "/templates", label: "Шаблоны" },
  { to: "/pricing", label: "Подписки" },
];

export function Layout({ children }: { children: ReactNode }) {
  const { balanceTokens, tier } = useUser();
  const loc = useLocation();

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <Link to="/" className={styles.brand}>
            <span className={styles.brandMark} aria-hidden />
            <span className={styles.brandText}>
              <span className={styles.brandName}>Bok Studio</span>
              <span className={styles.brandTag}>семейные истории</span>
            </span>
          </Link>

          <nav className={styles.nav} aria-label="Основное меню">
            {nav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `${styles.navLink} ${isActive ? styles.navLinkActive : ""}`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className={styles.headerRight}>
            <div className={styles.tokens} title="Баланс токенов (демо)">
              <span className={styles.tokenIcon} aria-hidden />
              <span className={styles.tokenValue}>
                {balanceTokens.toLocaleString("ru-RU")}
              </span>
              <span className={styles.tokenLabel}>токенов</span>
            </div>
            <span className={styles.tierBadge} title="Текущий план">
              {tier}
            </span>
          </div>
        </div>
      </header>

      <main
        className={styles.main}
        key={loc.pathname}
        data-route={loc.pathname}
      >
        {children}
      </main>

      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <p>
            Интерфейс-прототип. Генерация и оплата подключаются к вашему backend.
          </p>
          <Link to="/pricing">Тарифы и токены</Link>
        </div>
      </footer>
    </div>
  );
}
