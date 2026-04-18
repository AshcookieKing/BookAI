import ui from "@/components/ui.module.css";
import { PLANS, type SubscriptionTier } from "@/lib/subscriptions";
import { TOKEN_COSTS } from "@/lib/tokens";
import { useUser } from "@/context/UserContext";
import styles from "./PricingPage.module.css";

export function PricingPage() {
  const { setTier, setBalance, tier } = useUser();

  function pickPlan(id: SubscriptionTier) {
    setTier(id);
    const plan = PLANS.find((p) => p.id === id);
    if (plan) setBalance(plan.tokensMonthly);
  }

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <p className={styles.eyebrow}>Монетизация</p>
        <h1 className={ui.h1}>Подписки и токены</h1>
        <p className={ui.lead}>
          Токены списываются за фактические операции генерации. Цифры ниже —
          стартовая сетка для продукта; на backend вы подставите свои
          коэффициенты и валюту.
        </p>
      </header>

      <section className={`${ui.card} ${styles.tableCard}`} aria-label="Сетка токенов">
        <h2 className={styles.sectionTitle}>Базовые расходы (токены)</h2>
        <div className={styles.tokenGrid}>
          <div>
            <span className={styles.tk}>Изображение</span>
            <strong>{TOKEN_COSTS.imagePerUnit}</strong> за кадр
          </div>
          <div>
            <span className={styles.tk}>Редактирование фото</span>
            <strong>{TOKEN_COSTS.imageEditPerUnit}</strong> за кадр
          </div>
          <div>
            <span className={styles.tk}>Видео</span>
            <strong>{TOKEN_COSTS.videoPerSecond}</strong> за секунду
          </div>
          <div>
            <span className={styles.tk}>Текст истории</span>
            <strong>{TOKEN_COSTS.storyBase}</strong> база +{" "}
            <strong>{TOKEN_COSTS.storyPer1kChars}</strong> за 1k символов
          </div>
          <div>
            <span className={styles.tk}>Книга</span>
            <strong>{TOKEN_COSTS.bookBase}</strong> база +{" "}
            <strong>{TOKEN_COSTS.bookPerPage}</strong> за страницу
          </div>
          <div>
            <span className={styles.tk}>Озвучка</span>
            <strong>{TOKEN_COSTS.ttsPerMinute}</strong> за минуту
          </div>
        </div>
      </section>

      <section className={styles.plans} aria-label="Тарифы">
        {PLANS.map((p) => (
          <article
            key={p.id}
            className={`${ui.card} ${styles.plan} ${
              p.highlighted ? styles.planHighlight : ""
            }`}
          >
            {p.highlighted && (
              <span className={styles.ribbon}>Популярный</span>
            )}
            <h2 className={styles.planName}>{p.name}</h2>
            <p className={styles.tagline}>{p.tagline}</p>
            <p className={styles.price}>
              {p.priceMonthlyRub === null || p.priceMonthlyRub === 0 ? (
                "0 ₽"
              ) : (
                <>
                  {p.priceMonthlyRub.toLocaleString("ru-RU")} ₽
                  <span>/мес</span>
                </>
              )}
            </p>
            <p className={styles.tokens}>
              {p.tokensMonthly.toLocaleString("ru-RU")} токенов / месяц
            </p>
            <ul className={styles.perks}>
              {p.perks.map((x) => (
                <li key={x}>{x}</li>
              ))}
            </ul>
            <button
              type="button"
              className={`${ui.btn} ${
                p.highlighted ? ui.btnPrimary : ui.btnGhost
              }`}
              onClick={() => pickPlan(p.id)}
              disabled={tier === p.id}
            >
              {tier === p.id ? "Текущий план" : "Выбрать (демо)"}
            </button>
          </article>
        ))}
      </section>

      <p className={styles.footnote}>
        Демо-кнопки меняют план в интерфейсе и выставляют баланс равным месячной
        квоте токенов — для проверки UX без платёжного шлюза.
      </p>
    </div>
  );
}
