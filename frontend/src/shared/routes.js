export const AUTH_DESTINATIONS = Object.freeze([
  '/despesas',
  '/gastos',
  '/consolidado',
  '/configuracoes',
]);

const allowedDestinations = new Set(AUTH_DESTINATIONS);

export function safeAuthDestination(
  value,
  origin = globalThis.location?.origin ?? 'https://expenses.local',
) {
  try {
    const base = new URL(origin);
    const destination = new URL(value || '/despesas', base);
    return destination.origin === base.origin && allowedDestinations.has(destination.pathname)
      ? `${destination.pathname}${destination.search}`
      : '/despesas';
  } catch {
    return '/despesas';
  }
}
