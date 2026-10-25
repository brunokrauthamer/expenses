import Icon from '../ui/Icon.jsx';

export default function ActiveFilters({ filters, onClear, clearDisabled = false }) {
  if (!filters.length) return null;
  return (
    <div className="active-filters" aria-label="Filtros ativos">
      <span className="active-filters-label">Ativos</span>
      {filters.map((filter) => (
        <button
          className="filter-tag"
          type="button"
          key={filter.id ?? filter.label}
          onClick={filter.onRemove}
          aria-label={`Remover filtro ${filter.label}`}
        >
          <span>{filter.label}</span>
          <Icon name="close" size={14} />
        </button>
      ))}
      {onClear && (
        <button
          className="text-button clear-filters"
          type="button"
          onClick={onClear}
          disabled={clearDisabled}
        >
          Limpar filtros
        </button>
      )}
    </div>
  );
}
