export default function EmptyState({ eyebrow = 'Ainda sem registros', title, description }) {
  return (
    <div className="empty-state">
      <div className="empty-illustration" aria-hidden="true">
        <span>R$</span>
        <i>＋</i>
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
      <span className="empty-eyebrow">{eyebrow}</span>
    </div>
  );
}
