import './index.css';
import { CATALOGS } from './catalogs.js';
import CatalogSection from './CatalogSection/index.jsx';
import { useAuth } from '../../store/auth/useAuth.js';
import { useCategories } from '../../store/queries/useCategories.js';
import { usePaymentMethods } from '../../store/queries/usePaymentMethods.js';
import { useIncomeCategories } from '../../store/queries/useIncomeCategories.js';

export default function SettingsPage() {
  const { user } = useAuth();
  const userId = user?.id;
  const categoriesQuery = useCategories(userId, { includeDeleted: true });
  const incomeCategoriesQuery = useIncomeCategories(userId, { includeDeleted: true });
  const paymentMethodsQuery = usePaymentMethods(userId, { includeDeleted: true });

  const data = {
    categories: {
      items: categoriesQuery.data ?? [],
      isLoading: categoriesQuery.isLoading,
      error: categoriesQuery.error,
      refetch: categoriesQuery.refetch,
    },
    'income-categories': {
      items: incomeCategoriesQuery.data ?? [],
      isLoading: incomeCategoriesQuery.isLoading,
      error: incomeCategoriesQuery.error,
      refetch: incomeCategoriesQuery.refetch,
    },
    'payment-methods': {
      items: paymentMethodsQuery.data ?? [],
      isLoading: paymentMethodsQuery.isLoading,
      error: paymentMethodsQuery.error,
      refetch: paymentMethodsQuery.refetch,
    },
  };

  return (
    <>
      <section className="intro settings-intro">
        <p className="eyebrow">SEUS CADASTROS</p>
        <h1>
          Personalize <span>suas opções.</span>
        </h1>
        <p className="intro-copy">Altere seus cadastros sem perder o histórico dos lançamentos.</p>
      </section>
      <div className="settings-grid">
        {CATALOGS.map((config) => (
          <CatalogSection key={config.key} userId={userId} config={config} {...data[config.key]} />
        ))}
      </div>
    </>
  );
}
