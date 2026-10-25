import './index.css';
import { navigate } from '../../store/navigation.js';

export default function AppLink({ to, className, children, ...props }) {
  function follow(event) {
    props.onClick?.(event);
    if (
      event.defaultPrevented ||
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey ||
      props.target === '_blank'
    )
      return;

    const destination = new URL(to, window.location.origin);
    if (destination.origin !== window.location.origin) return;
    event.preventDefault();
    navigate(`${destination.pathname}${destination.search}${destination.hash}`);
  }

  return (
    <a {...props} className={className} href={to} onClick={follow}>
      {children}
    </a>
  );
}
