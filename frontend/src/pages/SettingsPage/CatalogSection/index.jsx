import Icon from '../../../components/ui/Icon.jsx';
import Panel from '../../../components/ui/Panel.jsx';
import SectionHeading from '../../../components/ui/SectionHeading.jsx';
import Button from '../../../components/Button/index.jsx';
import IconButton from '../../../components/IconButton/index.jsx';
import FormField from '../../../components/FormField/index.jsx';
import Input from '../../../components/Input/index.jsx';
import FeedbackMessage from '../../../components/FeedbackMessage/index.jsx';
import QueryFeedback from '../../../components/QueryFeedback/index.jsx';
import ConfirmDialog from '../../../components/ConfirmDialog/index.jsx';
import { useCatalogSection } from './useCatalogSection.js';

export default function CatalogSection({ userId, config, items, isLoading, error, refetch }) {
  const state = useCatalogSection(userId, config);
  const activeItems = items.filter((item) => !item.deleted_at);
  const deletedItems = items.filter((item) => item.deleted_at);

  return (
    <Panel className="settings-panel" aria-label={config.title}>
      <SectionHeading
        number={
          config.key === 'categories' ? '01' : config.key === 'income-categories' ? '02' : '03'
        }
        title={config.title}
        titleId={`${config.key}-title`}
        description={config.description}
      />
      <form className="settings-form" onSubmit={state.save}>
        <FormField
          className="full-field"
          label={state.editingItem ? 'Renomear cadastro' : 'Novo cadastro'}
        >
          <Input
            value={state.name}
            onChange={(event) => state.setName(event.target.value)}
            maxLength="50"
            placeholder="Digite um nome"
            disabled={state.isSaving}
          />
        </FormField>
        {config.hasReimbursementRule && (
          <label className="settings-rule">
            <input
              type="checkbox"
              checked={state.requiresReimbursement}
              onChange={(event) => state.setRequiresReimbursement(event.target.checked)}
              disabled={state.isSaving}
            />
            <span>
              <strong>Esta categoria representa um reembolso</strong>
              <small>Ela exigirá a categoria do gasto e reduzirá o gasto líquido.</small>
            </span>
          </label>
        )}
        {state.errorMessage && <FeedbackMessage type="error">{state.errorMessage}</FeedbackMessage>}
        {state.message && <FeedbackMessage type="success">{state.message}</FeedbackMessage>}
        <div className="settings-form-actions">
          <Button className="submit-button" type="submit" loading={state.isSaving}>
            <span>
              {state.isSaving ? 'Salvando…' : state.editingItem ? 'Salvar alterações' : 'Adicionar'}
            </span>
            <Icon name={state.editingItem ? 'edit' : 'entry'} size={17} />
          </Button>
          {state.editingItem && (
            <Button
              variant="text"
              className="text-button"
              onClick={state.cancelEditing}
              disabled={state.isSaving}
            >
              Cancelar edição
            </Button>
          )}
        </div>
      </form>

      <QueryFeedback
        error={error}
        isLoading={isLoading}
        hasData={items.length > 0}
        refetch={refetch}
        loadingMessage="Carregando cadastros…"
      />
      {!isLoading && !error && activeItems.length === 0 && (
        <p className="settings-empty">
          Nenhum cadastro ativo. Adicione um nome acima para usar em novos lançamentos.
        </p>
      )}
      {activeItems.length > 0 && (
        <ul className="settings-list" aria-label={`${config.title} ativos`}>
          {activeItems.map((item) => (
            <li className="settings-item" key={item.id}>
              <div>
                <strong>{item.name}</strong>
                {config.hasReimbursementRule && (
                  <small>
                    {item.requires_expense_category
                      ? 'Reembolso vinculado a uma categoria de despesa'
                      : 'Entrada sem vínculo de despesa'}
                  </small>
                )}
              </div>
              <div className="settings-item-actions">
                <IconButton
                  onClick={() => state.startEditing(item)}
                  aria-label={`Renomear ${item.name}`}
                  title="Renomear"
                >
                  <Icon name="edit" size={16} />
                </IconButton>
                <IconButton
                  className="delete-button"
                  onClick={() => state.requestDelete(item)}
                  aria-label={`Excluir ${item.name}`}
                  title="Excluir"
                >
                  <Icon name="trash" size={16} />
                </IconButton>
              </div>
            </li>
          ))}
        </ul>
      )}

      {deletedItems.length > 0 && (
        <details className="settings-archived">
          <summary>Excluídos ({deletedItems.length})</summary>
          <ul className="settings-list" aria-label={`${config.title} excluídos`}>
            {deletedItems.map((item) => (
              <li className="settings-item is-deleted" key={item.id}>
                <div>
                  <strong>{item.name}</strong>
                  <small>Preservado nos lançamentos anteriores</small>
                </div>
                <span className="archived-badge">Excluído</span>
              </li>
            ))}
          </ul>
        </details>
      )}

      <ConfirmDialog
        isOpen={Boolean(state.pendingDelete)}
        title={state.pendingDelete ? `Excluir “${state.pendingDelete.name}”?` : ''}
        description="Lançamentos anteriores serão preservados e continuarão aparecendo no histórico, nas buscas e nos relatórios."
        error={state.deleteError}
        confirmLabel="Excluir cadastro"
        pendingLabel="Excluindo…"
        isPending={state.isSaving}
        onCancel={state.cancelDelete}
        onConfirm={state.confirmDelete}
      />
    </Panel>
  );
}
