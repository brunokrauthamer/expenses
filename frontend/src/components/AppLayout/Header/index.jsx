import AppLink from '../../AppLink/index.jsx';
import Button from '../../Button/index.jsx';
import Icon from '../../ui/Icon.jsx';

export default function Header({ activeRoute, user, onSignOut }) {
  return (
    <header className="topbar">
      <AppLink className="brand" to="/despesas" aria-label="Expenses, cadastro de despesas">
        <span className="brand-mark" aria-hidden="true">
          e
        </span>
        <span>
          expenses<span className="brand-period">.</span>
        </span>
      </AppLink>
      <nav className="main-nav" aria-label="Navegação principal">
        <AppLink
          className={`nav-link${activeRoute === '/despesas' ? ' is-active' : ''}`}
          to="/despesas"
          aria-current={activeRoute === '/despesas' ? 'page' : undefined}
        >
          <Icon name="entry" /> Registrar despesas
        </AppLink>
        <AppLink
          className={`nav-link${activeRoute === '/consolidado' ? ' is-active' : ''}`}
          to="/consolidado"
          aria-current={activeRoute === '/consolidado' ? 'page' : undefined}
        >
          <Icon name="overview" /> Gastos consolidados
        </AppLink>
        <AppLink
          className={`nav-link${activeRoute === '/gastos' ? ' is-active' : ''}`}
          to="/gastos"
          aria-current={activeRoute === '/gastos' ? 'page' : undefined}
        >
          <Icon name="entry" /> Gastos do mês
        </AppLink>
        <AppLink
          className={`nav-link${activeRoute === '/configuracoes' ? ' is-active' : ''}`}
          to="/configuracoes"
          aria-current={activeRoute === '/configuracoes' ? 'page' : undefined}
        >
          <Icon name="settings" /> Configurações
        </AppLink>
      </nav>
      <div className="account-actions">
        <span className="topbar-note">
          <span className="status-dot" /> {user?.name || user?.email}
        </span>
        <Button variant="text" className="text-button signout-button" onClick={onSignOut}>
          Sair
        </Button>
      </div>
    </header>
  );
}
