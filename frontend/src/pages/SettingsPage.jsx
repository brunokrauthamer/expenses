import { useCallback, useEffect, useRef, useState } from 'react';
import Icon from '../components/ui/Icon.jsx';
import Panel from '../components/ui/Panel.jsx';
import SectionHeading from '../components/ui/SectionHeading.jsx';
import { api } from '../services/api.js';
import { invalidateCachedQueries, getQueryErrorMessage } from '../shared/queryCache.js';
import { useAuth } from '../shared/AuthContext.jsx';
import { useExpenseLookups } from '../shared/useExpenseLookups.js';

const CATALOGS = [
  {
    key: 'categories',
    title: 'Categorias de despesas',
    description: 'Organize as despesas com os nomes que fazem sentido para você.',
    create: (data) => api.createCategory({ name: data.name }),
    update: (id, data) => api.updateCategory(id, { name: data.name }),
    remove: (id) => api.deleteCategory(id),
  },
  {
    key: 'income-categories',
    title: 'Categorias de entradas',
    description: 'Classifique salários, reembolsos e outros valores recebidos.',
    create: (data) => api.createIncomeCategory(data),
    update: (id, data) => api.updateIncomeCategory(id, data),
    remove: (id) => api.deleteIncomeCategory(id),
    hasReimbursementRule: true,
  },
  {
    key: 'payment-methods',
    title: 'Meios de pagamento',
    description: 'Escolha os meios usados nos novos lançamentos.',
    create: (data) => api.createPaymentMethod({ name: data.name }),
    update: (id, data) => api.updatePaymentMethod(id, { name: data.name }),
    remove: (id) => api.deletePaymentMethod(id),
  },
];

function CatalogSection({ config, items, isLoading, error, onChanged }) {
  const [name, setName] = useState('');
  const [requiresReimbursement, setRequiresReimbursement] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [message, setMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const dialogRef = useRef(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (pendingDelete && !dialog.open) dialog.showModal();
    if (!pendingDelete && dialog.open) dialog.close();
  }, [pendingDelete]);

  function startEditing(item) {
    setEditingItem(item);
    setName(item.name);
    setRequiresReimbursement(Boolean(item.requires_expense_category));
    setMessage('');
    setErrorMessage('');
  }

  function cancelEditing() {
    setEditingItem(null);
    setName('');
    setRequiresReimbursement(false);
    setErrorMessage('');
  }

  async function save(event) {
    event.preventDefault();
    const normalizedName = name.trim();
    if (!normalizedName) {
      setErrorMessage('Informe um nome para este cadastro.');
      return;
    }
    setIsSaving(true);
    setErrorMessage('');
    setMessage('');
    const data = {
      name: normalizedName,
      ...(config.hasReimbursementRule ? { requires_expense_category: requiresReimbursement } : {}),
    };
    try {
      if (editingItem) await config.update(editingItem.id, data);
      else await config.create(data);
      onChanged();
      setMessage(editingItem ? 'Cadastro atualizado.' : 'Cadastro adicionado.');
      cancelEditing();
    } catch (requestError) {
      setErrorMessage(requestError.message || 'Não foi possível salvar este cadastro.');
    } finally {
      setIsSaving(false);
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return;
    setIsSaving(true);
    setErrorMessage('');
    try {
      await config.remove(pendingDelete.id);
      onChanged();
      setPendingDelete(null);
      setMessage('Cadastro excluído. Os lançamentos anteriores foram preservados.');
      if (editingItem?.id === pendingDelete.id) cancelEditing();
    } catch (requestError) {
      setErrorMessage(requestError.message || 'Não foi possível excluir este cadastro.');
    } finally {
      setIsSaving(false);
    }
  }

  const activeItems = items.filter((item) => !item.deleted_at);
  const deletedItems = items.filter((item) => item.deleted_at);

  return (
    <Panel className="settings-panel" aria-label={config.title}>
      <SectionHeading number={config.key === 'categories' ? '01' : config.key === 'income-categories' ? '02' : '03'} title={config.title} titleId={`${config.key}-title`} description={config.description} />
      <form className="settings-form" onSubmit={save}>
        <label className="field full-field">
          <span>{editingItem ? 'Renomear cadastro' : 'Novo cadastro'}</span>
          <input value={name} onChange={(event) => setName(event.target.value)} maxLength="50" placeholder="Digite um nome" disabled={isSaving} />
        </label>
        {config.hasReimbursementRule && <label className="settings-rule">
          <input type="checkbox" checked={requiresReimbursement} onChange={(event) => setRequiresReimbursement(event.target.checked)} disabled={isSaving} />
          <span><strong>Esta categoria representa um reembolso</strong><small>Ela exigirá a categoria do gasto e reduzirá o gasto líquido.</small></span>
        </label>}
        {errorMessage && <p className="form-message error-message" role="alert">{errorMessage}</p>}
        {message && <p className="form-message" role="status">{message}</p>}
        <div className="settings-form-actions">
          <button className="submit-button" type="submit" disabled={isSaving}>
            <span>{isSaving ? 'Salvando…' : editingItem ? 'Salvar alterações' : 'Adicionar'}</span>
            <Icon name={editingItem ? 'edit' : 'entry'} size={17} />
          </button>
          {editingItem && <button className="text-button" type="button" onClick={cancelEditing} disabled={isSaving}>Cancelar edição</button>}
        </div>
      </form>

      {isLoading && <p className="query-state" role="status">Carregando cadastros…</p>}
      {error && <div className="query-state error-state" role="alert"><p>{getQueryErrorMessage(error)}</p><button className="text-button" type="button" onClick={onChanged}>Tentar novamente</button></div>}
      {!isLoading && !error && activeItems.length === 0 && <p className="settings-empty">Nenhum cadastro ativo. Adicione um nome acima para usar em novos lançamentos.</p>}
      {activeItems.length > 0 && <ul className="settings-list" aria-label={`${config.title} ativos`}>
        {activeItems.map((item) => <li className="settings-item" key={item.id}>
          <div><strong>{item.name}</strong>{config.hasReimbursementRule && <small>{item.requires_expense_category ? 'Reembolso vinculado a uma categoria de despesa' : 'Entrada sem vínculo de despesa'}</small>}</div>
          <div className="settings-item-actions">
            <button className="icon-button" type="button" onClick={() => startEditing(item)} aria-label={`Renomear ${item.name}`} title="Renomear"><Icon name="edit" size={16} /></button>
            <button className="icon-button delete-button" type="button" onClick={() => { setErrorMessage(''); setPendingDelete(item); }} aria-label={`Excluir ${item.name}`} title="Excluir"><Icon name="trash" size={16} /></button>
          </div>
        </li>)}
      </ul>}

      {deletedItems.length > 0 && <details className="settings-archived">
        <summary>Excluídos ({deletedItems.length})</summary>
        <ul className="settings-list" aria-label={`${config.title} excluídos`}>
          {deletedItems.map((item) => <li className="settings-item is-deleted" key={item.id}><div><strong>{item.name}</strong><small>Preservado nos lançamentos anteriores</small></div><span className="archived-badge">Excluído</span></li>)}
        </ul>
      </details>}

      <dialog
        ref={dialogRef}
        className="delete-dialog"
        aria-labelledby={`${config.key}-delete-title`}
        aria-describedby={`${config.key}-delete-description`}
        onCancel={(event) => { event.preventDefault(); if (!isSaving) setPendingDelete(null); }}
        onClick={(event) => { if (event.target === event.currentTarget && !isSaving) setPendingDelete(null); }}
      >
        {pendingDelete && <div className="delete-dialog-content">
          <span className="delete-dialog-icon" aria-hidden="true"><Icon name="trash" size={20} /></span>
          <p className="delete-dialog-eyebrow">Excluir cadastro</p>
          <h2 id={`${config.key}-delete-title`}>Excluir “{pendingDelete.name}”?</h2>
          <p id={`${config.key}-delete-description`} className="delete-dialog-copy">Lançamentos anteriores serão preservados e continuarão aparecendo no histórico, nas buscas e nos relatórios.</p>
          {errorMessage && <p className="delete-dialog-error" role="alert">{errorMessage}</p>}
          <div className="delete-dialog-actions">
            <button className="delete-dialog-cancel" type="button" onClick={() => setPendingDelete(null)} disabled={isSaving}>Cancelar</button>
            <button className="delete-dialog-confirm" type="button" onClick={confirmDelete} disabled={isSaving}>{isSaving ? 'Excluindo…' : 'Excluir cadastro'}</button>
          </div>
        </div>}
      </dialog>
    </Panel>
  );
}

export default function SettingsPage() {
  const { user } = useAuth();
  const userId = user?.id;
  const lookups = useExpenseLookups(userId);
  const onChanged = useCallback(() => {
    invalidateCachedQueries([userId, 'lookups']);
    invalidateCachedQueries([userId, 'expenses']);
    invalidateCachedQueries([userId, 'income-entries']);
  }, [userId]);

  const data = {
    categories: { items: lookups.categoryReferences, isLoading: lookups.categoryReferencesQuery.isLoading, error: lookups.categoryReferencesQuery.error },
    'income-categories': { items: lookups.incomeCategoryReferences, isLoading: lookups.incomeCategoryReferencesQuery.isLoading, error: lookups.incomeCategoryReferencesQuery.error },
    'payment-methods': { items: lookups.paymentMethodReferences, isLoading: lookups.paymentMethodReferencesQuery.isLoading, error: lookups.paymentMethodReferencesQuery.error },
  };

  return <>
    <section className="intro settings-intro">
      <p className="eyebrow">SEUS CADASTROS</p>
      <h1>Personalize <span>suas opções.</span></h1>
      <p className="intro-copy">Altere seus cadastros sem perder o histórico dos lançamentos.</p>
    </section>
    <div className="settings-grid">
      {CATALOGS.map((config) => <CatalogSection key={config.key} config={config} {...data[config.key]} onChanged={onChanged} />)}
    </div>
  </>;
}
