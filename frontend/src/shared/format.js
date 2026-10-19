const currencyFormat = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
});

const integerFormat = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 });

const compactCurrencyFormat = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  notation: 'compact',
  maximumFractionDigits: 1,
});

const dateFormat = new Intl.DateTimeFormat('pt-BR', {
  dateStyle: 'medium',
  timeZone: 'UTC',
});

const monthFormat = new Intl.DateTimeFormat('pt-BR', {
  month: 'short',
  year: '2-digit',
  timeZone: 'UTC',
});

export function formatMoney(value) {
  const match = /^(-?)(\d+)(?:[.,](\d*))?$/.exec(String(value ?? '0').trim());
  if (!match) {
    const numericValue = Number(value);
    return currencyFormat.format(Number.isFinite(numericValue) ? numericValue : 0);
  }

  const wholeAmount = BigInt(match[2]);
  const fraction = (match[3] ?? '').padEnd(2, '0').slice(0, 2);
  const cents = wholeAmount * 100n + BigInt(fraction || '0');
  const parts = currencyFormat.formatToParts(match[1] ? -1 : 1);
  return parts.map((part) => {
    if (part.type === 'integer') return integerFormat.format(cents / 100n);
    if (part.type === 'fraction') return fraction;
    return part.value;
  }).join('');
}

export function formatAmountInput(value) {
  const digits = String(value ?? '').replace(/\D/g, '').slice(0, 12);
  if (!digits) return '';

  const integer = digits.length > 2 ? digits.slice(0, -2) : '0';
  const fraction = digits.slice(-2).padStart(2, '0');
  return `${Number(integer).toLocaleString('pt-BR')},${fraction}`;
}

export function formatCompactMoney(value) {
  const numericValue = Number(value);
  return compactCurrencyFormat.format(Number.isFinite(numericValue) ? numericValue : 0);
}

export function formatDate(value) {
  return dateFormat.format(new Date(`${value}T00:00:00Z`));
}

export function formatMonth(value) {
  return monthFormat.format(new Date(`${value}-01T00:00:00Z`)).replace('.', '');
}

export function todayISO() {
  const now = new Date();
  const month = `${now.getMonth() + 1}`.padStart(2, '0');
  return `${now.getFullYear()}-${month}-${`${now.getDate()}`.padStart(2, '0')}`;
}

export function currentMonthISO() {
  return todayISO().slice(0, 7);
}

export function shiftMonth(month, offset) {
  const [year, monthNumber] = month.split('-').map(Number);
  const shifted = new Date(Date.UTC(year, monthNumber - 1 + offset, 1));
  return `${shifted.getUTCFullYear()}-${`${shifted.getUTCMonth() + 1}`.padStart(2, '0')}`;
}

export function monthDistance(startMonth, endMonth) {
  const [startYear, startNumber] = startMonth.split('-').map(Number);
  const [endYear, endNumber] = endMonth.split('-').map(Number);
  return (endYear - startYear) * 12 + endNumber - startNumber;
}
