import { useEffect, useState } from 'react';
import Icon from './Icon.jsx';

export default function DebouncedSearchField({ value, onCommit }) {
  const [draft, setDraft] = useState(value);

  useEffect(() => setDraft(value), [value]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const normalizedValue = draft.trim();
      if (normalizedValue !== value) onCommit(normalizedValue);
    }, 400);
    return () => window.clearTimeout(timer);
  }, [draft, value, onCommit]);

  return (
    <label className="field full-field search-field">
      <span>Buscar</span>
      <div className="search-input-wrap">
        <span aria-hidden="true">
          <Icon name="search" size={17} />
        </span>
        <input
          name="search"
          type="search"
          maxLength="100"
          autoComplete="off"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Descrição, categoria ou meio de pagamento"
          aria-label="Buscar despesas por descricao, categoria ou meio de pagamento"
        />
      </div>
    </label>
  );
}
