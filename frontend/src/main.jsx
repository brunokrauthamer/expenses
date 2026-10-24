import React, { Suspense, lazy, useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import { AppLink, navigate, useLocation } from './shared/router.jsx';
import Icon from './components/ui/Icon.jsx';
import AuthPage from './pages/AuthPage.jsx';
import GoogleAuthComplete from './pages/GoogleAuthComplete.jsx';
import { AuthProvider, useAuth } from './shared/AuthContext.jsx';
import './styles.css';
import './viewport.css';

const ExpensesPage = lazy(() => import('./pages/ExpensesPage.jsx'));
const ReportsPage = lazy(() => import('./pages/ReportsPage.jsx'));
const ExpenseHistoryPage = lazy(() => import('./pages/ExpenseHistoryPage.jsx'));
const SettingsPage = lazy(() => import('./pages/SettingsPage.jsx'));
const AUTH_DESTINATIONS = new Set(['/despesas', '/gastos', '/consolidado', '/configuracoes']);

function safeAuthDestination(value) {
  try {
    const destination = new URL(value || '/despesas', window.location.origin);
    return destination.origin === window.location.origin && AUTH_DESTINATIONS.has(destination.pathname)
      ? `${destination.pathname}${destination.search}`
      : '/despesas';
  } catch {
    return '/despesas';
  }
}

function Header({ activeRoute, user, onSignOut }) {
  return (
    <header className="topbar">
      <AppLink className="brand" to="/despesas" aria-label="Expenses, cadastro de despesas">
        <span className="brand-mark" aria-hidden="true">e</span>
        <span>expenses<span className="brand-period">.</span></span>
      </AppLink>
      <nav className="main-nav" aria-label="Navegação principal">
        <AppLink className={`nav-link${activeRoute === '/despesas' ? ' is-active' : ''}`} to="/despesas" aria-current={activeRoute === '/despesas' ? 'page' : undefined}>
          <Icon name="entry" /> Registrar despesas
        </AppLink>
        <AppLink className={`nav-link${activeRoute === '/consolidado' ? ' is-active' : ''}`} to="/consolidado" aria-current={activeRoute === '/consolidado' ? 'page' : undefined}>
          <Icon name="overview" /> Gastos consolidados
        </AppLink>
        <AppLink className={`nav-link${activeRoute === '/gastos' ? ' is-active' : ''}`} to="/gastos" aria-current={activeRoute === '/gastos' ? 'page' : undefined}>
          <Icon name="entry" /> Gastos do mês
        </AppLink>
        <AppLink className={`nav-link${activeRoute === '/configuracoes' ? ' is-active' : ''}`} to="/configuracoes" aria-current={activeRoute === '/configuracoes' ? 'page' : undefined}>
          <Icon name="settings" /> Configurações
        </AppLink>
      </nav>
      <div className="account-actions">
        <span className="topbar-note"><span className="status-dot" /> {user?.name || user?.email}</span>
        <button className="text-button signout-button" type="button" onClick={onSignOut}>Sair</button>
      </div>
    </header>
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
  const { user, status, signOut } = useAuth();
  const pathname = location.split('?')[0];
  const activeRoute = pathname === '/' ? '/despesas' : pathname;
  const isAuthRoute = pathname === '/entrar' || pathname === '/cadastro';
  const authNext = safeAuthDestination(new URLSearchParams(location.split('?')[1] ?? '').get('next'));

  useEffect(() => {
    if (status === 'loading') return;
    if (isAuthRoute && status === 'authenticated') navigate(authNext, { replace: true });
    else if (!isAuthRoute && status === 'anonymous' && pathname !== '/') {
      navigate(`/entrar?next=${encodeURIComponent(location)}`, { replace: true });
    } else if (pathname === '/') navigate(status === 'authenticated' ? '/despesas' : '/entrar', { replace: true });
  }, [pathname, location, status, isAuthRoute, authNext]);

  if (status === 'loading') {
    return <div className="auth-loading" role="status">Verificando sua sessão…</div>;
  }

  if (isAuthRoute) {
    return <div className="page-shell auth-shell"><main className="app-content"><AuthPage mode={pathname === '/cadastro' ? 'register' : 'login'} /></main><Footer /></div>;
  }

  if (status !== 'authenticated') return <div className="auth-loading" role="status">Redirecionando para o login…</div>;

  let page;
  if (activeRoute === '/despesas') page = <ExpensesPage />;
  else if (activeRoute === '/consolidado') page = <ReportsPage />;
  else if (activeRoute === '/gastos') page = <ExpenseHistoryPage />;
  else if (activeRoute === '/configuracoes') page = <SettingsPage />;
  else page = (
    <section className="panel route-error" aria-labelledby="not-found-heading">
      <span className="step-number">404</span>
      <h1 id="not-found-heading">Essa página não foi encontrada.</h1>
      <AppLink className="text-link" to="/despesas">Voltar ao cadastro</AppLink>
    </section>
  );

  return (
    <div className="page-shell">
      <Header activeRoute={activeRoute} user={user} onSignOut={signOut} />
      <main className="app-content" id="conteudo">
        <Suspense fallback={<div className="route-loading" role="status">Abrindo sua página…</div>}>
          <div className="route-view">{page}</div>
        </Suspense>
      </main>
      <Footer />
    </div>
  );
}

function Root() {
  const location = useLocation();
  if (location.split('?')[0] === '/auth/complete') return <GoogleAuthComplete />;
  return <AuthProvider><App /></AuthProvider>;
}

createRoot(document.getElementById('root')).render(<React.StrictMode><Root /></React.StrictMode>);
