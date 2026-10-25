import './index.css';

export default function FeedbackMessage({ type = 'info', children, className = '', ...props }) {
  const role = type === 'error' ? 'alert' : 'status';
  return (
    <p
      {...props}
      className={`form-message feedback-message feedback-message--${type}${className ? ` ${className}` : ''}`}
      role={role}
    >
      {children}
    </p>
  );
}
