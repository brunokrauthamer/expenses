import React, { Suspense, lazy, useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import { AppLink, navigate, useLocation } from './shared/router.jsx';
import Icon from './components/ui/Icon.jsx';
import './styles.css';

const ExpensesPage = lazy(() => import('./pages/ExpensesPage.jsx'));
const ReportsPage = lazy(() => import('./pages/ReportsPage.jsx'));

function Header({ activeRoute }) {
  return (
    <>
      <header className="topbar">
        <AppLink className="brand" to="/despesas" aria-label="Expenses, cadastro de despesas">
          <span className="brand-mark" aria-hidden="true">e</span>
          <span>expenses<span className="brand-period">.</span></span>
        </AppLink>
        <span className="topbar-note"><span className="status-dot" /> Seu espaço financeiro</span>
      </header>
      <nav className="main-nav" aria-label="Navegação principal">
        <AppLink className={`nav-link${activeRoute === '/despesas' ? ' is-active' : ''}`} to="/despesas" aria-current={activeRoute === '/despesas' ? 'page' : undefined}>
          <Icon name="entry" /> Registrar despesas
        </AppLink>
        <AppLink className={`nav-link${activeRoute === '/consolidado' ? ' is-active' : ''}`} to="/consolidado" aria-current={activeRoute === '/consolidado' ? 'page' : undefined}>
          <Icon name="overview" /> Gastos consolidados
        </AppLink>
      </nav>
    </>
  );
}

function Footer() {
  return (
    <footer className="footer">
      <span>Um jeito simples de acompanhar seus gastos.</span>
      <span>EXPENSES <i>·</i> {new Date().getFullYear()}</span>
    </footer>
  );
}

function App() {
  const location = useLocation();
  const pathname = location.split('?')[0];
  const activeRoute = pathname === '/' ? '/despesas' : pathname;

  useEffect(() => {
    if (pathname === '/') navigate('/despesas', { replace: true });
  }, [pathname]);

  let page;
  if (activeRoute === '/despesas') page = <ExpensesPage />;
  else if (activeRoute === '/consolidado') page = <ReportsPage />;
  else page = (
    <section className="panel route-error" aria-labelledby="not-found-heading">
      <span className="step-number">404</span>
      <h1 id="not-found-heading">Essa página não foi encontrada.</h1>
      <AppLink className="text-link" to="/despesas">Voltar ao cadastro</AppLink>
    </section>
  );

  return (
    <div className="page-shell">
      <Header activeRoute={activeRoute} />
      <main className="app-content" id="conteudo">
        <Suspense fallback={<div className="route-loading" role="status">Abrindo sua página…</div>}>
          <div className="route-view">{page}</div>
        </Suspense>
      </main>
      <Footer />
    </div>
  );
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode><App /></React.StrictMode>,
);
