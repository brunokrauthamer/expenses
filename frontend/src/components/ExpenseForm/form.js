import { formatAmountInput, todayISO } from '../../shared/format.js';
import { normalizeMoneyAmount } from '../../shared/money.js';

export function newExpenseForm(today = todayISO()) {
  return {
    description: '',
    amount: '',
    expenseDate: today,
    categoryId: '',
    paymentMethodId: '',
    paymentType: 'one_time',
    installmentCount: '2',
    amountType: 'total',
    firstInstallmentDate: today,
  };
}

export function expenseFormFromRecord(expense) {
  return {
    description: expense.description,
    amount: formatAmountInput(String(expense.total_amount).replace(/\D/g, '')),
    expenseDate: expense.expense_date,
    categoryId: String(expense.category_id),
    paymentMethodId: String(expense.payment_method_id),
    paymentType: expense.payment_type,
    installmentCount: String(expense.installment_count),
    amountType: 'total',
    firstInstallmentDate: expense.first_installment_date,
  };
}

export function buildExpensePayload(form) {
  if (!form.description.trim()) {
    return { field: 'description', message: 'Informe uma descrição para esta despesa.' };
  }

  const amount = normalizeMoneyAmount(form.amount);
  if (!amount) {
    return {
      field: 'amount',
      message: 'Informe um valor maior que zero, com até duas casas decimais.',
    };
  }

  const installmentCount = form.paymentType === 'installments' ? Number(form.installmentCount) : 1;
  const minimumInstallments = form.paymentType === 'installments' ? 2 : 1;
  if (
    !Number.isInteger(installmentCount) ||
    installmentCount < minimumInstallments ||
    installmentCount > 1200
  ) {
    return {
      field: 'installmentCount',
      message: 'Informe uma quantidade válida de parcelas, de 2 a 1.200.',
    };
  }
  if (!form.categoryId || !form.paymentMethodId) {
    return {
      field: !form.categoryId ? 'categoryId' : 'paymentMethodId',
      message: 'Escolha uma categoria e um meio de pagamento.',
    };
  }
  if (form.paymentType === 'installments' && form.firstInstallmentDate < form.expenseDate) {
    return {
      field: 'firstInstallmentDate',
      message: 'A primeira parcela não pode anteceder a data da compra.',
    };
  }

  return {
    payload: {
      description: form.description.trim(),
      amount,
      expense_date: form.expenseDate,
      category_id: Number(form.categoryId),
      payment_method_id: Number(form.paymentMethodId),
      payment_type: form.paymentType,
      amount_type: form.paymentType === 'installments' ? form.amountType : 'total',
      installment_count: installmentCount,
      ...(form.paymentType === 'installments'
        ? { first_installment_date: form.firstInstallmentDate }
        : {}),
    },
  };
}
