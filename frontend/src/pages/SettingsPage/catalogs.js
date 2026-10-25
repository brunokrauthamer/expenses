export const CATALOGS = Object.freeze([
  {
    key: 'categories',
    catalog: 'categories',
    title: 'Categorias de despesas',
    description: 'Organize as despesas com os nomes que fazem sentido para você.',
  },
  {
    key: 'income-categories',
    catalog: 'incomeCategories',
    title: 'Categorias de entradas',
    description: 'Classifique salários, reembolsos e outros valores recebidos.',
    hasReimbursementRule: true,
  },
  {
    key: 'payment-methods',
    catalog: 'paymentMethods',
    title: 'Meios de pagamento',
    description: 'Escolha os meios usados nos novos lançamentos.',
  },
]);
