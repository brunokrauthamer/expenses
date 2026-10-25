import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, test, vi } from 'vitest';
import Button from './index.jsx';

test('a regular button does not submit its surrounding form', async () => {
  const user = userEvent.setup();
  const onSubmit = vi.fn((event) => event.preventDefault());
  const onClick = vi.fn();

  render(
    <form onSubmit={onSubmit}>
      <Button onClick={onClick}>Cancelar</Button>
      <Button type="submit">Salvar</Button>
    </form>,
  );

  await user.click(screen.getByRole('button', { name: 'Cancelar' }));

  expect(onClick).toHaveBeenCalledOnce();
  expect(onSubmit).not.toHaveBeenCalled();
});

test('a pending button is disabled and ignores clicks', async () => {
  const user = userEvent.setup();
  const onClick = vi.fn();

  render(
    <Button loading onClick={onClick}>
      Salvando
    </Button>,
  );

  const button = screen.getByRole('button', { name: 'Salvando' });
  expect(button).toBeDisabled();
  expect(button).toHaveAttribute('aria-busy', 'true');

  await user.click(button);

  expect(onClick).not.toHaveBeenCalled();
});
