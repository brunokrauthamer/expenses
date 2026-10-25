export default function Footer() {
  return (
    <footer className="footer">
      <span>Um jeito simples de acompanhar seus gastos.</span>
      <span>
        EXPENSES <i>·</i> {new Date().getFullYear()}
      </span>
    </footer>
  );
}
