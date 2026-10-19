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

export function AppLink({ to, className, children, ...props }) {
  function follow(event) {
    props.onClick?.(event);
    if (
      event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey ||
      event.shiftKey || event.altKey || props.target === '_blank'
    ) return;

    const destination = new URL(to, window.location.origin);
    if (destination.origin !== window.location.origin) return;
    event.preventDefault();
    navigate(`${destination.pathname}${destination.search}${destination.hash}`);
  }

  return <a {...props} className={className} href={to} onClick={follow}>{children}</a>;
}
