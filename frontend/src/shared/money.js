export function normalizeMoneyAmount(input) {
  let value = String(input ?? '')
    .trim()
    .replace(/[R$\s]/gi, '');
  if (value.includes(',')) value = value.replace(/\./g, '').replace(',', '.');
  if (!/^\d{1,10}(?:\.\d{1,2})?$/.test(value)) return null;

  const [integer, fraction = ''] = value.split('.');
  const normalizedInteger = integer.replace(/^0+(?=\d)/, '');
  const normalizedFraction = fraction.padEnd(2, '0');
  if (normalizedInteger === '0' && normalizedFraction === '00') return null;
  return `${normalizedInteger}.${normalizedFraction}`;
}

export function decimalToCents(value) {
  const match = /^(-?)(\d+)(?:[.,](\d{1,2}))?$/.exec(String(value ?? '0').trim());
  if (!match) return null;
  const magnitude = BigInt(match[2]) * 100n + BigInt((match[3] ?? '').padEnd(2, '0') || '0');
  return match[1] ? -magnitude : magnitude;
}

export function centsToDecimal(cents) {
  const value = BigInt(cents);
  const negative = value < 0n;
  const magnitude = negative ? -value : value;
  return `${negative ? '-' : ''}${magnitude / 100n}.${String(magnitude % 100n).padStart(2, '0')}`;
}

export function sumMovementAmounts(movements = []) {
  const cents = movements.reduce((total, movement) => {
    const amount = decimalToCents(
      movement.amount_due ?? movement.installment_amount ?? movement.amount ?? '0',
    );
    if (amount === null) return total;
    return total + (movement.kind === 'reimbursement' ? -amount : amount);
  }, 0n);
  return centsToDecimal(cents);
}
