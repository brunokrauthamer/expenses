import { useMemo, useState } from 'react';

const categories = ['Alimentação', 'Transporte', 'Moradia', 'Saúde', 'Lazer', 'Compras', 'Outros'];
const money = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

function today() {
  const date = new Date();
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 10);
}

function displayDate(value) {
  return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium', timeZone: 'UTC' }).format(
    new Date(`${value}T00:00:00Z`),
  );
}

export default function App() {
  const [expenses, setExpenses] = useState([]);
  const [form, setForm] = useState({ description: '', amount: '', category: '', date: today() });
  const total = useMemo(() => expenses.reduce((sum, expense) => sum + expense.amount, 0), [expenses]);

  function updateField(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  function addExpense(event) {
    event.preventDefault();
    const amount = Number(form.amount);
    if (!form.description.trim() || !Number.isFinite(amount) || amount <= 0 || !form.category || !form.date) return;
    setExpenses((current) => [{ ...form, id: crypto.randomUUID(), description: form.description.trim(), amount }, ...current]);
    setForm({ description: '', amount: '', category: '', date: today() });
  }

  function removeExpense(id) {
    setExpenses((current) => current.filter((expense) => expense.id !== id));
  }

  return (
    <main className="page-shell">
      <header className="topbar">
        <a className="brand" href="#inicio" aria-label="Expenses, início">
          <span className="brand-mark" aria-hidden="true">e</span>
          <span>expenses<span className="brand-period">.</span></span>
        </a>
        <span className="topbar-note"><span className="status-dot" /> Seu espaço financeiro</span>
      </header>

      <section className="intro" id="inicio">
        <p className="eyebrow">CONTROLE PESSOAL</p>
        <h1>Suas despesas,<br /><span>no seu ritmo.</span></h1>
        <p className="intro-copy">Um lugar simples para acompanhar o que você gasta.</p>
      </section>

      <section className="summary-card" aria-label="Resumo das despesas">
        <div>
          <p className="summary-label">TOTAL DE DESPESAS</p>
          <p className="summary-total">{money.format(total)}</p>
          <p className="summary-caption">{expenses.length === 1 ? '1 despesa registrada' : `${expenses.length} despesas registradas`}</p>
        </div>
        <div className="summary-icon" aria-hidden="true">↗</div>
        <div className="summary-decoration" aria-hidden="true" />
      </section>

      <div className="content-grid">
        <section className="panel form-panel">
          <div className="section-heading">
            <span className="step-number">01</span>
            <div><h2>Nova despesa</h2><p>Registre um gasto do seu dia.</p></div>
          </div>
          <form onSubmit={addExpense}>
            <label className="field full-field">
              <span>Descrição</span>
              <input name="description" value={form.description} onChange={updateField} placeholder="Ex.: almoço de hoje" maxLength="80" required />
            </label>
            <div className="field-row">
              <label className="field">
                <span>Valor</span>
                <div className="input-with-prefix"><span>R$</span><input name="amount" type="number" min="0.01" step="0.01" inputMode="decimal" value={form.amount} onChange={updateField} placeholder="0,00" required /></div>
              </label>
              <label className="field">
                <span>Data</span>
                <input name="date" type="date" value={form.date} onChange={updateField} required />
              </label>
            </div>
            <label className="field full-field">
              <span>Categoria</span>
              <select name="category" value={form.category} onChange={updateField} required>
                <option value="" disabled>Escolha uma categoria</option>
                {categories.map((category) => <option key={category} value={category}>{category}</option>)}
              </select>
            </label>
            <button className="submit-button" type="submit"><span>Adicionar despesa</span><span aria-hidden="true">＋</span></button>
          </form>
          <p className="form-footnote"><span aria-hidden="true">✳</span> Seus dados ficam só nesta sessão.</p>
        </section>

        <section className="panel list-panel">
          <div className="section-heading list-heading">
            <span className="step-number">02</span>
            <div><h2>Despesas</h2><p>O que já entrou na sua lista.</p></div>
            <span className="count-badge">{expenses.length}</span>
          </div>
          {expenses.length === 0 ? (
            <div className="empty-state">
              <div className="empty-illustration" aria-hidden="true"><span>R$</span><i>＋</i></div>
              <h3>Tudo começa com um registro.</h3>
              <p>Adicione sua primeira despesa<br />e ela aparece aqui.</p>
            </div>
          ) : (
            <ul className="expense-list">
              {expenses.map((expense) => (
                <li className="expense-item" key={expense.id}>
                  <span className="expense-symbol" aria-hidden="true">{expense.category.slice(0, 1)}</span>
                  <div className="expense-details"><strong>{expense.description}</strong><span>{expense.category} <i>·</i> {displayDate(expense.date)}</span></div>
                  <strong className="expense-amount">{money.format(expense.amount)}</strong>
                  <button className="delete-button" type="button" onClick={() => removeExpense(expense.id)} aria-label={`Excluir despesa ${expense.description}`} title="Excluir despesa">×</button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <footer className="footer"><span>Um jeito simples de acompanhar seus gastos.</span><span>EXPENSES <i>·</i> 2026</span></footer>
    </main>
  );
}
