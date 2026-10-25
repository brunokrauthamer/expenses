import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { expect, test, vi } from 'vitest';
import ConfirmDialog from './index.jsx';

function DialogHarness({ onConfirm = vi.fn(), onCancel = vi.fn() }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <button type="button" onClick={() => setIsOpen(true)}>
        Abrir confirmação
      </button>
      <ConfirmDialog
        isOpen={isOpen}
        title="Excluir item?"
        description="O item será removido do histórico."
        onConfirm={onConfirm}
        onCancel={() => {
          onCancel();
          setIsOpen(false);
        }}
      />
    </>
  );
}

test('opening focuses cancel and closing returns focus to the trigger', async () => {
  const user = userEvent.setup();
  render(<DialogHarness />);

  const trigger = screen.getByRole('button', { name: 'Abrir confirmação' });
  await user.click(trigger);

  const dialog = screen.getByRole('dialog');
  expect(dialog).toHaveAttribute('open');
  expect(screen.getByRole('button', { name: 'Cancelar' })).toHaveFocus();

  await user.click(screen.getByRole('button', { name: 'Cancelar' }));

  expect(dialog.open).toBe(false);
  expect(trigger).toHaveFocus();
});

test('a cancel event calls the cancel action and prevents the browser from closing first', () => {
  const onCancel = vi.fn();
  render(
    <ConfirmDialog
      isOpen
      title="Excluir item?"
      description="Confirme a remoção."
      onConfirm={vi.fn()}
      onCancel={onCancel}
    />,
  );

  const event = new Event('cancel', { cancelable: true });
  fireEvent(screen.getByRole('dialog'), event);

  expect(onCancel).toHaveBeenCalledOnce();
  expect(event.defaultPrevented).toBe(true);
});

test('pending confirmation disables both actions and ignores cancellation', () => {
  const onConfirm = vi.fn();
  const onCancel = vi.fn();
  render(
    <ConfirmDialog
      isOpen
      isPending
      title="Excluir item?"
      description="Confirme a remoção."
      pendingLabel="Excluindo…"
      onConfirm={onConfirm}
      onCancel={onCancel}
    />,
  );

  const dialog = screen.getByRole('dialog');
  const cancelEvent = new Event('cancel', { cancelable: true });
  fireEvent(dialog, cancelEvent);

  expect(screen.getByRole('button', { name: 'Cancelar' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Excluindo…' })).toBeDisabled();
  expect(cancelEvent.defaultPrevented).toBe(true);
  expect(onCancel).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole('button', { name: 'Excluindo…' }));
  expect(onConfirm).not.toHaveBeenCalled();
});
