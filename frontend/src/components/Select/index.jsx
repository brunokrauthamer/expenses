import { forwardRef } from 'react';

const Select = forwardRef(function Select({ className = '', children, ...props }, ref) {
  return (
    <select {...props} ref={ref} className={`select${className ? ` ${className}` : ''}`}>
      {children}
    </select>
  );
});

export default Select;
