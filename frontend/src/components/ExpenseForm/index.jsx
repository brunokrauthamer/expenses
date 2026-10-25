import './index.css';
import { memo, useEffect, useRef, useState } from 'react';
import Icon from '../ui/Icon.jsx';
import SectionHeading from '../ui/SectionHeading.jsx';
import Button from '../Button/index.jsx';
import FormField from '../FormField/index.jsx';
import Input from '../Input/index.jsx';
import Select from '../Select/index.jsx';
import MoneyInput from '../MoneyInput/index.jsx';
import FeedbackMessage from '../FeedbackMessage/index.jsx';
import { formatAmountInput } from '../../shared/format.js';
import { buildExpensePayload, expenseFormFromRecord, newExpenseForm } from './form.js';
import { saveExpense } from '../../store/mutations/expenses.js';

const ExpenseForm = memo(function ExpenseForm({
  userId,
  categories,
  categoryReferences = categories,
  paymentMethods,
  paymentMethodReferences = paymentMethods,
  expenseToEdit,
  onCancelEdit,
  onSaved,
}) {
  const [form, setForm] = useState(() =>
    expenseToEdit ? expenseFormFromRecord(expenseToEdit) : newExpenseForm(),
  );
  const [error, setError] = useState('');
  const [errorField, setErrorField] = useState('');
  const [success, setSuccess] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [keepFields, setKeepFields] = useState(false);
  const descriptionRef = useRef(null);
  const categoryOptions = [
    ...categories,
    ...categoryReferences.filter(
      (item) => item.deleted_at && item.id === expenseToEdit?.category_id,
    ),
  ];
  const paymentMethodOptions = [
    ...paymentMethods,
    ...paymentMethodReferences.filter(
      (item) => item.deleted_at && item.id === expenseToEdit?.payment_method_id,
    ),
  ];

  useEffect(() => {
    if (expenseToEdit) descriptionRef.current?.focus({ preventScroll: true });
  }, [expenseToEdit]);

  const updateField = (event) => {
    const { name, value } = event.target;
    const nextValue = name === 'amount' ? formatAmountInput(value) : value;
    setForm((current) => ({
      ...current,
      [name]: nextValue,
      ...(name === 'paymentType' && value === 'installments' && Number(current.installmentCount) < 2
        ? { installmentCount: '2' }
        : {}),
      ...(name === 'expenseDate' && current.firstInstallmentDate === current.expenseDate
        ? { firstInstallmentDate: value }
        : {}),
    }));
    setError('');
    setErrorField('');
    setSuccess('');
  };

  function showFieldError(field, message) {
    setErrorField(field);
    setError(message);
  }

  async function submitExpense(event) {
    event.preventDefault();
    if (!form.description.trim()) {
      showFieldError('description', 'Informe uma descrição para esta despesa.');
      return;
    }
    const validation = buildExpensePayload(form);
    if (!validation.payload) {
      showFieldError(validation.field, validation.message);
      return;
    }
    const payload = validation.payload;
    setIsSaving(true);
    setError('');
    setErrorField('');
    setSuccess('');
    try {
      const saved = await saveExpense(userId, expenseToEdit?.id, payload);
      if (expenseToEdit) {
        setForm(expenseFormFromRecord(saved));
      } else {
        setForm(() => {
          const next = newExpenseForm();
          if (keepFields) {
            next.description = form.description;
            next.categoryId = form.categoryId;
            next.paymentMethodId = form.paymentMethodId;
            next.paymentType = form.paymentType;
          }
          return next;
        });
      }
      if (expenseToEdit) onSaved?.(saved);
      setSuccess(expenseToEdit ? 'Despesa atualizada com sucesso.' : 'Despesa salva com sucesso.');
    } catch (requestError) {
      setError(requestError.message || 'Não foi possível salvar esta despesa.');
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <form onSubmit={submitExpense} className="expense-form">
      <SectionHeading
        number="01"
        title={expenseToEdit ? 'Editar despesa' : 'Nova despesa'}
        description={
          expenseToEdit ? 'Atualize os dados desta compra.' : 'Registre uma compra do seu dia.'
        }
        trailing={
          expenseToEdit && (
            <Button variant="text" className="text-button cancel-edit" onClick={onCancelEdit}>
              Cancelar
            </Button>
          )
        }
      />
      <div
        className="form-fields scroll-region"
        role="region"
        aria-label="Dados da despesa"
        tabIndex="0"
      >
        <FormField
          className="full-field"
          label="Descrição"
          required
          error={errorField === 'description' ? error : undefined}
        >
          <Input
            ref={descriptionRef}
            name="description"
            value={form.description}
            onChange={updateField}
            placeholder="Ex.: compras da semana"
            maxLength="120"
            autoComplete="off"
            required
          />
        </FormField>

        <div className="field-row">
          <FormField
            label={
              form.paymentType === 'installments' && form.amountType === 'installment'
                ? 'Valor da parcela'
                : 'Valor'
            }
            required
            error={errorField === 'amount' ? error : undefined}
          >
            <MoneyInput
              name="amount"
              type="text"
              autoComplete="off"
              value={form.amount}
              onChange={updateField}
              placeholder="0,00"
              aria-label="Valor em reais"
              required
            />
          </FormField>
          <FormField
            label="Data da compra"
            required
            error={errorField === 'expenseDate' ? error : undefined}
          >
            <Input
              name="expenseDate"
              type="date"
              value={form.expenseDate}
              onChange={updateField}
              required
            />
          </FormField>
        </div>

        <FormField
          label="Categoria"
          required
          error={errorField === 'categoryId' ? error : undefined}
        >
          <Select name="categoryId" value={form.categoryId} onChange={updateField} required>
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

        <FormField
          label="Meio de pagamento"
          required
          error={errorField === 'paymentMethodId' ? error : undefined}
        >
          <Select
            name="paymentMethodId"
            value={form.paymentMethodId}
            onChange={updateField}
            required
          >
            <option value="" disabled>
              Selecione
            </option>
            {paymentMethodOptions.map((method) => (
              <option key={method.id} value={method.id}>
                {method.name}
                {method.deleted_at ? ' (excluído)' : ''}
              </option>
            ))}
          </Select>
        </FormField>

        <fieldset className="payment-choice">
          <legend>Pagamento</legend>
          <label
            className={`choice-option${form.paymentType === 'one_time' ? ' is-selected' : ''}`}
          >
            <input
              type="radio"
              name="paymentType"
              value="one_time"
              checked={form.paymentType === 'one_time'}
              onChange={updateField}
            />
            <span>À vista</span>
          </label>
          <label
            className={`choice-option${form.paymentType === 'installments' ? ' is-selected' : ''}`}
          >
            <input
              type="radio"
              name="paymentType"
              value="installments"
              checked={form.paymentType === 'installments'}
              onChange={updateField}
            />
            <span>Parcelado</span>
          </label>
        </fieldset>

        {form.paymentType === 'installments' && (
          <div className="installment-fields">
            <div className="field-row">
              <FormField
                label="Quantidade"
                required
                error={errorField === 'installmentCount' ? error : undefined}
              >
                <Input
                  name="installmentCount"
                  type="number"
                  inputMode="numeric"
                  min="2"
                  max="1200"
                  step="1"
                  value={form.installmentCount}
                  onChange={updateField}
                  required
                />
              </FormField>
              <FormField label="O valor informado é">
                <Select name="amountType" value={form.amountType} onChange={updateField}>
                  <option value="total">Total da compra</option>
                  <option value="installment">Cada parcela</option>
                </Select>
              </FormField>
            </div>
            <FormField
              className="full-field"
              label="Data da primeira parcela"
              required
              error={errorField === 'firstInstallmentDate' ? error : undefined}
            >
              <Input
                name="firstInstallmentDate"
                type="date"
                min={form.expenseDate}
                value={form.firstInstallmentDate}
                onChange={updateField}
                required
              />
            </FormField>
          </div>
        )}
      </div>
      {!expenseToEdit && (
        <label className="keep-fields-option">
          <input
            type="checkbox"
            checked={keepFields}
            onChange={(event) => setKeepFields(event.target.checked)}
          />
          <span>
            Manter descrição, categoria, meio de pagamento e pagamento para a próxima despesa
          </span>
        </label>
      )}
      {error && !errorField && <FeedbackMessage type="error">{error}</FeedbackMessage>}
      {success && <FeedbackMessage type="success">{success}</FeedbackMessage>}
      <Button className="submit-button" type="submit" loading={isSaving}>
        <span>
          {isSaving ? 'Salvando...' : expenseToEdit ? 'Salvar alterações' : 'Adicionar despesa'}
        </span>
        <Icon name={expenseToEdit ? 'edit' : 'entry'} />
      </Button>
    </form>
  );
});

export default ExpenseForm;
