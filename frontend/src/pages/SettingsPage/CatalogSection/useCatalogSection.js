import { useState } from 'react';
import { saveCatalogItem, removeCatalogItem } from '../../../store/mutations/catalogs.js';

export function useCatalogSection(userId, config) {
  const [name, setName] = useState('');
  const [requiresReimbursement, setRequiresReimbursement] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [message, setMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [deleteError, setDeleteError] = useState('');
  const [isSaving, setIsSaving] = useState(false);

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
      await saveCatalogItem(userId, config.catalog, editingItem?.id, data);
      setMessage(editingItem ? 'Cadastro atualizado.' : 'Cadastro adicionado.');
      cancelEditing();
    } catch (requestError) {
      setErrorMessage(requestError.message || 'Não foi possível salvar este cadastro.');
    } finally {
      setIsSaving(false);
    }
  }

  function requestDelete(item) {
    setDeleteError('');
    setPendingDelete(item);
  }

  function cancelDelete() {
    if (isSaving) return;
    setPendingDelete(null);
    setDeleteError('');
  }

  async function confirmDelete() {
    if (!pendingDelete) return;
    setIsSaving(true);
    setDeleteError('');
    try {
      await removeCatalogItem(userId, config.catalog, pendingDelete.id);
      setPendingDelete(null);
      setMessage('Cadastro excluído. Os lançamentos anteriores foram preservados.');
      if (editingItem?.id === pendingDelete.id) cancelEditing();
    } catch (requestError) {
      setDeleteError(requestError.message || 'Não foi possível excluir este cadastro.');
    } finally {
      setIsSaving(false);
    }
  }

  return {
    name,
    setName,
    requiresReimbursement,
    setRequiresReimbursement,
    editingItem,
    pendingDelete,
    message,
    errorMessage,
    deleteError,
    isSaving,
    startEditing,
    cancelEditing,
    requestDelete,
    cancelDelete,
    save,
    confirmDelete,
  };
}
