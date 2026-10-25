import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { expect, test } from 'vitest';
import FormField from '../FormField/index.jsx';
import Select from './index.jsx';

function CategorySelect() {
  const [category, setCategory] = useState('');

  return (
    <FormField label="Categoria" required>
      <Select value={category} onChange={(event) => setCategory(event.target.value)}>
        <option value="">Escolha uma categoria</option>
        <option value="moradia">Moradia</option>
      </Select>
    </FormField>
  );
}

test('a labelled native select changes its controlled value', async () => {
  const user = userEvent.setup();

  render(<CategorySelect />);

  const select = screen.getByRole('combobox', { name: 'Categoria' });
  expect(select).toBeRequired();

  await user.selectOptions(select, 'moradia');

  expect(select).toHaveValue('moradia');
});
