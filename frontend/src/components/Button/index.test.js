import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import reactPlugin from '@vitejs/plugin-react';
import { createServer } from 'vite';

let vite;
let Button;
let IconButton;
let FormField;
let Input;
let Select;
let ConfirmDialog;

before(async () => {
  vite = await createServer({
    configFile: false,
    plugins: [reactPlugin()],
    server: { middlewareMode: true },
    appType: 'custom',
  });
  [Button, IconButton, FormField, Input, Select, ConfirmDialog] = await Promise.all([
    vite.ssrLoadModule('/src/components/Button/index.jsx').then((module) => module.default),
    vite.ssrLoadModule('/src/components/IconButton/index.jsx').then((module) => module.default),
    vite.ssrLoadModule('/src/components/FormField/index.jsx').then((module) => module.default),
    vite.ssrLoadModule('/src/components/Input/index.jsx').then((module) => module.default),
    vite.ssrLoadModule('/src/components/Select/index.jsx').then((module) => module.default),
    vite.ssrLoadModule('/src/components/ConfirmDialog/index.jsx').then((module) => module.default),
  ]);
});

after(async () => vite?.close());

test('Button defaults to a non-submit action and exposes a pending state', () => {
  const regular = renderToStaticMarkup(React.createElement(Button, null, 'Cancelar'));
  assert.match(regular, /type="button"/);
  assert.doesNotMatch(regular, /disabled/);

  const pending = renderToStaticMarkup(
    React.createElement(Button, { type: 'submit', loading: true }, 'Salvar'),
  );
  assert.match(pending, /type="submit"/);
  assert.match(pending, /disabled=""/);
  assert.match(pending, /aria-busy="true"/);
});

test('IconButton requires an accessible name', () => {
  assert.throws(
    () => renderToStaticMarkup(React.createElement(IconButton, null, '×')),
    /nome acessível/,
  );
  const markup = renderToStaticMarkup(
    React.createElement(IconButton, { 'aria-label': 'Excluir' }, '×'),
  );
  assert.match(markup, /aria-label="Excluir"/);
  assert.match(markup, /type="button"/);
});

test('FormField connects a label, required control, and field error', () => {
  const markup = renderToStaticMarkup(
    React.createElement(
      FormField,
      { label: 'E-mail', required: true, error: 'Informe o e-mail.' },
      React.createElement(Input, { type: 'email' }),
    ),
  );
  const id = markup.match(/for="([^"]+)"/)[1];
  assert.match(markup, new RegExp(`id="${id}"`));
  assert.match(markup, /required=""/);
  assert.match(markup, /aria-invalid="true"/);
  assert.match(markup, /role="alert"/);
});

test('Select keeps native options and controlled attributes', () => {
  const markup = renderToStaticMarkup(
    React.createElement(
      Select,
      { value: 'active', disabled: true, onChange() {} },
      React.createElement('option', { value: 'active' }, 'Ativa'),
    ),
  );
  assert.match(markup, /<select[^>]*disabled=""/);
  assert.match(markup, /<option value="active" selected="">Ativa/);
});

test('ConfirmDialog exposes a labelled description and pending confirmation state', () => {
  const markup = renderToStaticMarkup(
    React.createElement(ConfirmDialog, {
      isOpen: true,
      title: 'Excluir item?',
      description: 'O item será removido do histórico.',
      name: 'Compra de teste',
      isPending: true,
      pendingLabel: 'Excluindo…',
      onConfirm() {},
      onCancel() {},
    }),
  );
  assert.match(markup, /aria-labelledby="confirm-title-/);
  assert.match(markup, /aria-describedby="confirm-description-/);
  assert.match(markup, /aria-busy="true"/);
  assert.match(markup, /Compra de teste/);
  assert.match(markup, /Excluindo…/);
});
