import '../ExpenseForm/index.css';
import { memo, useState } from 'react';
import Icon from '../ui/Icon.jsx';
import SectionHeading from '../ui/SectionHeading.jsx';
import FeedbackMessage from '../FeedbackMessage/index.jsx';
import AppLink from '../AppLink/index.jsx';
import Button from '../Button/index.jsx';
import FormField from '../FormField/index.jsx';
import Input from '../Input/index.jsx';
import Select from '../Select/index.jsx';
import MoneyInput from '../MoneyInput/index.jsx';
import { formatAmountInput, todayISO } from '../../shared/format.js';
import { buildIncomePayload } from './form.js';
import { saveIncomeEntry } from '../../store/mutations/incomeEntries.js';

const IncomeForm = memo(function IncomeForm({
  userId,
  categories,
  categoryReferences = categories,
  incomeCategories,
  incomeCategoryReferences = incomeCategories,
  entryToEdit,
  onSaved,
  onCancel,
}) {
  const [description, setDescription] = useState(entryToEdit?.description ?? '');
  const [amount, setAmount] = useState(
    entryToEdit ? formatAmountInput(String(entryToEdit.amount).replace(/\D/g, '')) : '',
  );
  const [receivedDate, setReceivedDate] = useState(entryToEdit?.received_date ?? todayISO());
  const [incomeCategoryId, setIncomeCategoryId] = useState(
    entryToEdit ? String(entryToEdit.income_category_id) : '',
  );
  const [expenseCategoryId, setExpenseCategoryId] = useState(
    entryToEdit?.expense_category_id ? String(entryToEdit.expense_category_id) : '',
  );
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('info');
  const [isSaving, setIsSaving] = useState(false);
  const categoryOptions = [
    ...categories,
    ...categoryReferences.filter(
      (item) => item.deleted_at && item.id === entryToEdit?.expense_category_id,
    ),
  ];
  const incomeCategoryOptions = [
    ...incomeCategories,
    ...incomeCategoryReferences.filter(
      (item) => item.deleted_at && item.id === entryToEdit?.income_category_id,
    ),
  ];
  const selectedCategory = incomeCategoryOptions.find(
    (category) => String(category.id) === incomeCategoryId,
  );

  async function submit(event) {
    event.preventDefault();
    const validation = buildIncomePayload({
      description,
      amount,
      receivedDate,
      incomeCategoryId,
      expenseCategoryId,
      selectedCategory,
    });
    if (!validation.payload) {
      setMessageType('error');
      setMessage(validation.error);
      return;
    }
    setIsSaving(true);
    setMessage('');
    try {
      await saveIncomeEntry(userId, entryToEdit?.id, validation.payload);
      if (!entryToEdit) {
        setDescription('');
        setAmount('');
      }
      onSaved?.();
      setMessageType('success');
      setMessage('Entrada salva com sucesso.');
    } catch (error) {
      setMessageType('error');
      setMessage(error.message || 'Não foi possível salvar esta entrada.');
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <form className="expense-form" onSubmit={submit}>
      <SectionHeading
        number="01"
        title={entryToEdit ? 'Editar entrada' : 'Nova entrada'}
        description="Registre um valor recebido."
        trailing={
          entryToEdit && (
            <Button variant="text" className="text-button" onClick={onCancel}>
              Cancelar
            </Button>
          )
        }
      />
      <div
        className="form-fields scroll-region"
        role="region"
        aria-label="Dados da entrada"
        tabIndex="0"
      >
        <FormField className="full-field" label="Descrição" required>
          <Input
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            maxLength="120"
            required
            placeholder="Ex.: salário de outubro"
          />
        </FormField>
        <div className="field-row">
          <FormField label="Valor recebido" required>
            <MoneyInput
              value={amount}
              onChange={(event) => setAmount(formatAmountInput(event.target.value))}
              placeholder="0,00"
              required
            />
          </FormField>
          <FormField label="Data do recebimento" required>
            <Input
              type="date"
              value={receivedDate}
              onChange={(event) => setReceivedDate(event.target.value)}
              required
            />
          </FormField>
        </div>
        <FormField label="Categoria da entrada" required>
          <Select
            value={incomeCategoryId}
            onChange={(event) => {
              setIncomeCategoryId(event.target.value);
              setExpenseCategoryId('');
            }}
            required
          >
            <option value="" disabled>
              Selecione
            </option>
            {incomeCategoryOptions.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
                {category.deleted_at ? ' (excluída)' : ''}
              </option>
            ))}
          </Select>
        </FormField>
        {!incomeCategoryOptions.length && (
          <p className="form-message error-message">
            Você não tem categorias de entrada ativas.{' '}
            <AppLink className="text-link" to="/configuracoes">
              Adicione uma em Configurações
            </AppLink>
            .
          </p>
        )}
        {selectedCategory?.requires_expense_category && (
          <FormField label="Categoria do gasto reembolsado" required>
            <Select
              value={expenseCategoryId}
              onChange={(event) => setExpenseCategoryId(event.target.value)}
              required
            >
              <option value="" disabled>
                Selecione
              </option>
              {categoryOptions.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                  {category.deleted_at ? ' (excluída)' : ''}
                </option>
              ))}
            </Select>
          </FormField>
        )}
      </div>
      {message && <FeedbackMessage type={messageType}>{message}</FeedbackMessage>}
      <Button
        className="submit-button"
        type="submit"
        disabled={!incomeCategories.length}
        loading={isSaving}
      >
        <span>
          {isSaving ? 'Salvando…' : entryToEdit ? 'Salvar alterações' : 'Adicionar entrada'}
        </span>
        <Icon name="entry" />
      </Button>
    </form>
  );
});

export default IncomeForm;
