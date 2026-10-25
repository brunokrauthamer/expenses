import './index.css';
import { useEffect, useId, useRef } from 'react';
import Button from '../Button/index.jsx';
import Icon from '../ui/Icon.jsx';

export default function ConfirmDialog({
  isOpen,
  title,
  description,
  name,
  error,
  confirmLabel = 'Confirmar',
  cancelLabel = 'Cancelar',
  pendingLabel = 'Aguarde…',
  isPending = false,
  onConfirm,
  onCancel,
  children,
}) {
  const dialogRef = useRef(null);
  const cancelRef = useRef(null);
  const previousFocusRef = useRef(null);
  const id = useId();
  const titleId = `confirm-title-${id}`;
  const descriptionId = `confirm-description-${id}`;

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return undefined;
    if (isOpen && !dialog.open) {
      previousFocusRef.current = document.activeElement;
      dialog.showModal();
      cancelRef.current?.focus({ preventScroll: true });
    } else if (!isOpen && dialog.open) {
      dialog.close();
      if (previousFocusRef.current instanceof HTMLElement && previousFocusRef.current.isConnected) {
        previousFocusRef.current.focus({ preventScroll: true });
      }
    }
    return undefined;
  }, [isOpen]);

  useEffect(
    () => () => {
      const dialog = dialogRef.current;
      if (dialog?.open) dialog.close();
      if (previousFocusRef.current instanceof HTMLElement && previousFocusRef.current.isConnected) {
        previousFocusRef.current.focus({ preventScroll: true });
      }
    },
    [],
  );

  function cancel(event) {
    event.preventDefault();
    if (!isPending) onCancel?.();
  }

  return (
    <dialog
      ref={dialogRef}
      className="delete-dialog"
      aria-labelledby={titleId}
      aria-describedby={description ? descriptionId : undefined}
      aria-busy={isPending || undefined}
      onCancel={cancel}
      onClick={(event) => {
        if (event.target === event.currentTarget && !isPending) onCancel?.();
      }}
    >
      <div className="delete-dialog-content">
        <span className="delete-dialog-icon" aria-hidden="true">
          <Icon name="trash" size={20} />
        </span>
        <p className="delete-dialog-eyebrow">Confirmação</p>
        <h2 id={titleId}>{title}</h2>
        {name && <p className="delete-dialog-name">{name}</p>}
        {description && (
          <p id={descriptionId} className="delete-dialog-copy">
            {description}
          </p>
        )}
        {children}
        {error && (
          <p className="delete-dialog-error" role="alert">
            {error}
          </p>
        )}
        <div className="delete-dialog-actions">
          <Button
            ref={cancelRef}
            variant="secondary"
            className="delete-dialog-cancel"
            onClick={onCancel}
            disabled={isPending}
          >
            {cancelLabel}
          </Button>
          <Button
            variant="danger"
            className="delete-dialog-confirm"
            onClick={onConfirm}
            disabled={isPending}
            loading={isPending}
          >
            {isPending ? pendingLabel : confirmLabel}
          </Button>
        </div>
      </div>
    </dialog>
  );
}
