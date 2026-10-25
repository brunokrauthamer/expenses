import Icon from './Icon.jsx';

const iconsByCategory = {
  mercado: 'basket',
  lazer: 'ticket',
  restaurante: 'utensils',
  transporte: 'bus',
  carro: 'car',
  presentes: 'gift',
  faxina: 'sparkles',
  servicos: 'wrench',
  cuidados: 'heart',
  saude: 'medical',
  viagem: 'plane',
  boletos: 'receipt',
  moradia: 'home',
  itens: 'sofa',
};

function normalizeCategoryName(name) {
  return name
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('pt-BR');
}

export default function CategoryIcon({ name, size = 18, ...props }) {
  const normalizedName = normalizeCategoryName(name);
  const iconName =
    Object.entries(iconsByCategory).find(([key]) => normalizedName.startsWith(key))?.[1] ?? 'tag';
  return <Icon name={iconName} size={size} {...props} />;
}
