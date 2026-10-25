import { forwardRef } from 'react';
import Button from '../Button/index.jsx';

const IconButton = forwardRef(function IconButton(
  { icon, children, 'aria-label': ariaLabel, ...props },
  ref,
) {
  if (!ariaLabel && !props['aria-labelledby']) {
    throw new Error('IconButton precisa de um nome acessível em aria-label ou aria-labelledby.');
  }
  return (
    <Button
      {...props}
      ref={ref}
      variant="icon"
      className={`icon-button${props.className ? ` ${props.className}` : ''}`}
      aria-label={ariaLabel}
    >
      {icon ?? children}
    </Button>
  );
});

export default IconButton;
