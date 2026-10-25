export function isValidMonth(value) {
  return /^\d{4}-(0[1-9]|1[0-2])$/.test(value ?? '') && Number(value.slice(0, 4)) > 0;
}
