import Header from './Header/index.jsx';
import Footer from './Footer/index.jsx';

export default function AppLayout({ activeRoute, user, onSignOut, children }) {
  return (
    <div className="page-shell app-layout">
      <Header activeRoute={activeRoute} user={user} onSignOut={onSignOut} />
      <main className="app-content" id="conteudo">
        {children}
      </main>
      <Footer />
    </div>
  );
}
