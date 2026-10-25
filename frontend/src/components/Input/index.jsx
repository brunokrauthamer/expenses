import { forwardRef } from 'react';

const Input = forwardRef(function Input({ className = '', ...props }, ref) {
  return <input {...props} ref={ref} className={`input${className ? ` ${className}` : ''}`} />;
});

export default Input;
