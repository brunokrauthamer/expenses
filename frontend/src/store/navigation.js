import { useSyncExternalStore } from 'react';

function subscribeToLocation(listener) {
  window.addEventListener('popstate', listener);
  return () => window.removeEventListener('popstate', listener);
}

function getLocation() {
  return `${window.location.pathname}${window.location.search}`;
}

export function useLocation() {
  return useSyncExternalStore(subscribeToLocation, getLocation, () => '/');
}

export function navigate(to, { replace = false, scroll = true } = {}) {
  if (replace) window.history.replaceState({}, '', to);
  else window.history.pushState({}, '', to);
  window.dispatchEvent(new PopStateEvent('popstate'));
  if (scroll) window.scrollTo({ top: 0, behavior: 'smooth' });
}
