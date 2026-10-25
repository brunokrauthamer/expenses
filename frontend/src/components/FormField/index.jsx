import { cloneElement, isValidElement, useId } from 'react';

function mergeIds(...values) {
  return [
    ...new Set(
      values.flatMap((value) =>
        String(value ?? '')
          .split(/\s+/)
          .filter(Boolean),
      ),
    ),
  ].join(' ');
}

export default function FormField({
  label,
  htmlFor,
  hint,
  error,
  required = false,
  className = '',
  children,
}) {
  const generatedId = useId();
  const control = isValidElement(children) ? children : null;
  const controlId = htmlFor ?? control?.props.id ?? `field-${generatedId}`;
  const hintId = hint ? `${controlId}-hint` : undefined;
  const errorId = error ? `${controlId}-error` : undefined;
  const describedBy = mergeIds(control?.props['aria-describedby'], hintId, errorId);
  const enhancedControl = control
    ? cloneElement(control, {
        id: control.props.id ?? controlId,
        required: control.props.required ?? required,
        'aria-describedby': describedBy || undefined,
        'aria-invalid': error ? true : control.props['aria-invalid'],
      })
    : children;

  return (
    <div className={`field form-field${className ? ` ${className}` : ''}`}>
      {label && <label htmlFor={controlId}>{label}</label>}
      {enhancedControl}
      {hint && (
        <span className="field-hint" id={hintId}>
          {hint}
        </span>
      )}
      {error && (
        <span className="field-error" id={errorId} role="alert">
          {error}
        </span>
      )}
    </div>
  );
}

export { mergeIds };
