import { render, screen } from '@testing-library/react';
import { expect, test } from 'vitest';
import Input from '../Input/index.jsx';
import FormField from './index.jsx';

test('the label, required state, hint, and error are connected to the control', () => {
  render(
    <FormField label="E-mail" hint="Usado para entrar." error="Informe um e-mail válido." required>
      <Input type="email" />
    </FormField>,
  );

  const input = screen.getByRole('textbox', { name: 'E-mail' });
  const describedBy = input.getAttribute('aria-describedby').split(' ');

  expect(input).toBeRequired();
  expect(input).toHaveAttribute('aria-invalid', 'true');
  expect(document.getElementById(describedBy[0])).toHaveTextContent('Usado para entrar.');
  expect(document.getElementById(describedBy[1])).toHaveTextContent('Informe um e-mail válido.');
  expect(screen.getByRole('alert')).toHaveTextContent('Informe um e-mail válido.');
});
