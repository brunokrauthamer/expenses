export default function FinancialSummaryCard({
  label,
  value,
  caption,
  className = '',
  children,
  ...props
}) {
  const ariaLabel = label ?? props['aria-label'];
  return (
    <section
      {...props}
      className={`report-total financial-summary-card${className ? ` ${className}` : ''}`}
      aria-label={ariaLabel}
    >
      {label && <span className="summary-label">{label}</span>}
      {value !== undefined && <strong className="summary-total">{value}</strong>}
      {caption && <span className="summary-caption">{caption}</span>}
      {children}
    </section>
  );
}
