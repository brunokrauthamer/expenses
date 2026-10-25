import './App.css';
import { lazy, Suspense, useEffect } from 'react';
import AppLink from './components/AppLink/index.jsx';
import AppLayout from './components/AppLayout/index.jsx';
import Footer from './components/AppLayout/Footer/index.jsx';
import AuthPage from './pages/AuthPage/index.jsx';
import GoogleAuthComplete from './pages/GoogleAuthComplete/index.jsx';
import { AuthProvider } from './store/auth/AuthProvider.jsx';
import { useAuth } from './store/auth/useAuth.js';
import { navigate, useLocation } from './store/navigation.js';
import { safeAuthDestination } from './shared/routes.js';

const ExpensesPage = lazy(() => import('./pages/ExpensesPage/index.jsx'));
const ReportsPage = lazy(() => import('./pages/ReportsPage/index.jsx'));
const ExpenseHistoryPage = lazy(() => import('./pages/ExpenseHistoryPage/index.jsx'));
const SettingsPage = lazy(() => import('./pages/SettingsPage/index.jsx'));

function RouteContent({ page }) {
  return (
    <Suspense
      fallback={
        <div className="route-loading" role="status">
          Abrindo sua página…
        </div>
      }
    >
      <div className="route-view">{page}</div>
    </Suspense>
  );
}

function AuthenticatedApp() {
  const location = useLocation();
  const { user, status, signOut } = useAuth();
  const pathname = location.split('?')[0];
  const activeRoute = pathname === '/' ? '/despesas' : pathname;
  const isAuthRoute = pathname === '/entrar' || pathname === '/cadastro';
  const authNext = safeAuthDestination(
    new URLSearchParams(location.split('?')[1] ?? '').get('next'),
  );

  useEffect(() => {
    if (status === 'loading') return;
    if (isAuthRoute && status === 'authenticated') navigate(authNext, { replace: true });
    else if (!isAuthRoute && status === 'anonymous' && pathname !== '/') {
      navigate(`/entrar?next=${encodeURIComponent(location)}`, { replace: true });
    } else if (pathname === '/')
      navigate(status === 'authenticated' ? '/despesas' : '/entrar', { replace: true });
  }, [pathname, location, status, isAuthRoute, authNext]);

  if (status === 'loading')
    return (
      <div className="auth-loading" role="status">
        Verificando sua sessão…
      </div>
    );
  if (isAuthRoute) {
    return (
      <div className="page-shell auth-shell">
        <main className="app-content">
          <AuthPage mode={pathname === '/cadastro' ? 'register' : 'login'} />
        </main>
        <Footer />
      </div>
    );
  }
  if (status !== 'authenticated')
    return (
      <div className="auth-loading" role="status">
        Redirecionando para o login…
      </div>
    );

  let page;
  if (activeRoute === '/despesas') page = <ExpensesPage />;
  else if (activeRoute === '/consolidado') page = <ReportsPage />;
  else if (activeRoute === '/gastos') page = <ExpenseHistoryPage />;
  else if (activeRoute === '/configuracoes') page = <SettingsPage />;
  else
    page = (
      <section className="panel route-error" aria-labelledby="not-found-heading">
        <span className="step-number">404</span>
        <h1 id="not-found-heading">Essa página não foi encontrada.</h1>
        <AppLink className="text-link" to="/despesas">
          Voltar ao cadastro
        </AppLink>
      </section>
    );

  return (
    <AppLayout activeRoute={activeRoute} user={user} onSignOut={signOut}>
      <RouteContent page={page} />
    </AppLayout>
  );
}

export default function App() {
  const location = useLocation();
  if (location.split('?')[0] === '/auth/complete') return <GoogleAuthComplete />;
  return (
    <AuthProvider>
      <AuthenticatedApp />
    </AuthProvider>
  );
}
