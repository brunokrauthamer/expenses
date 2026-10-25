import { forwardRef } from 'react';
import Input from '../Input/index.jsx';

const MoneyInput = forwardRef(function MoneyInput({ className = '', ...props }, ref) {
  return (
    <div className={`input-with-prefix money-input${className ? ` ${className}` : ''}`}>
      <span aria-hidden="true">R$</span>
      <Input {...props} ref={ref} inputMode={props.inputMode ?? 'numeric'} />
    </div>
  );
});

export default MoneyInput;
