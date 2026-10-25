import { formatMoney } from '../../../shared/format.js';
import { categoryColor } from '../../../shared/categoryColors.js';

export default function CategoryChart({ totals, categories, isUpdating }) {
  const maximum = Math.max(0, ...totals.map((item) => Math.abs(Number(item.amount_due))));
  const rows = totals.map((item) => {
    const category = categories.find((record) => record.id === item.category_id);
    return {
      ...item,
      name: `${category?.name ?? 'Categoria'}${category?.deleted_at ? ' (excluída)' : ''}`,
      percent:
        maximum === 0 ? 0 : Math.max((Math.abs(Number(item.amount_due)) / maximum) * 100, 1.5),
      color: categoryColor(item.category_id),
    };
  });

  return (
    <div className={`category-chart${isUpdating ? ' is-updating' : ''}`}>
      {rows.map((row, index) => (
        <div className="category-row" key={row.category_id}>
          <div className="category-row-label">
            <span
              className="category-dot"
              style={{ backgroundColor: row.color }}
              aria-hidden="true"
            />
            <span className="category-name" title={row.name}>
              {row.name}
            </span>
            <strong className="category-value">{formatMoney(row.amount_due)}</strong>
          </div>
          <div
            className="category-track"
            role="img"
            aria-label={`${row.name}: ${formatMoney(row.amount_due)}`}
            title={`${row.name}: ${formatMoney(row.amount_due)}`}
          >
            <div
              className="category-fill"
              style={{
                width: `${row.percent}%`,
                backgroundColor: row.color,
                transitionDelay: `${index * 25}ms`,
              }}
            />
          </div>
        </div>
      ))}
      <details className="chart-data-table">
        <summary>Ver valores em tabela</summary>
        <table>
          <caption>Total das cobranças por categoria no período selecionado</caption>
          <thead>
            <tr>
              <th>Categoria</th>
              <th>Valor</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.category_id}>
                <th scope="row">{row.name}</th>
                <td>{formatMoney(row.amount_due)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}
