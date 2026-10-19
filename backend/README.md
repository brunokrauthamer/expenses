# Backend do Expenses

O backend usa FastAPI, SQLAlchemy, Alembic e PostgreSQL. A API oferece cadastro, edição, exclusão e consulta mensal de gastos, incluindo parcelamentos.

## Organização

O projeto é um monólito modular. Cada domínio fica em `app/modules/` e separa:

- `model.py`: representação das tabelas pelo SQLAlchemy;
- `schema.py`: contratos de entrada e saída da API;
- `service.py`: regras e consultas do domínio;
- `controller.py`: rotas HTTP do domínio.

Os módulos existentes são `categories`, `expenses` e `payment_methods`. Código compartilhado fica em `app/shared/`; conexão e configuração ficam na raiz de `app/`.

## Configuração

1. Crie um banco PostgreSQL.
2. Copie `.env.example` para `.env` e ajuste `DATABASE_URL`.
3. Crie e ative um ambiente virtual Python.
4. Instale as dependências: `pip install -r requirements.txt`.
5. Aplique as migrações: `alembic upgrade head`.

As migrações criam `categories`, `payment_methods`, `expenses` e `expense_installments`. Para inserir as categorias e os meios de pagamento iniciais, execute a partir de `backend`:

```powershell
python -m app.seed
```

O seeder pode ser executado novamente; ele insere apenas os nomes ausentes.

## Gastos e parcelamentos

`POST /expenses` e `PUT /expenses/{expense_id}` recebem os campos atuais `description`, `amount`, `expense_date`, `category_id` e `payment_method_id`, além de:

- `payment_type`: `one_time` (padrão) ou `installments`;
- `installment_count`: quantidade de parcelas, de 1 a 1200; parcelados precisam de pelo menos 2;
- `amount_type`: `total` (padrão) ou `installment`;
- `first_installment_date`: opcional; por padrão, usa `expense_date`.

`amount` representa o total quando `amount_type` é `total`, ou o valor de cada parcela quando é `installment`. O total da compra fica salvo em `expenses.amount`. Para um total parcelado, as parcelas após a primeira usam a divisão arredondada para baixo a duas casas; a primeira recebe o restante, para que a soma coincida com o total. Por exemplo, R$ 100,01 em 3 vezes resulta em R$ 33,35, R$ 33,33 e R$ 33,33. As datas seguintes mantêm o dia da primeira cobrança, usando o último dia do mês quando o dia original não existe.

`GET /expenses` lista cobranças programadas, não compras únicas. Com `month=AAAA-MM`, retorna somente cobranças daquele mês; `start_month` e `end_month` filtram um intervalo inclusivo de até 120 meses. O intervalo não pode ser enviado junto com `month`. Também aceita `category_id` e `payment_method_id`; esses parâmetros podem ser combinados com busca e período. `amount_due` é o valor da parcela daquela linha e `total_amount` é o total da compra. O campo `id` continua sendo o gasto, utilizado nas rotas PUT e DELETE; `installment_id` identifica a cobrança. `total` na paginação conta cobranças.

Para o frontend:

- `GET /categories` e `GET /payment-methods` retornam as referências em ordem alfabética.
- `GET /expenses/recent?limit=10` retorna compras únicas em ordem de cadastro mais recente (`created_at`, com o ID como desempate). O limite aceito é de 1 a 50.
- `GET /expenses/summary` exige `start_month` e `end_month` (`AAAA-MM`) e aceita também `category_id`, `payment_method_id` e `search`. Retorna `total_amount_due`, uma lista de `monthly_totals` e outra de `category_totals`. O total é a soma das cobranças dentro dos filtros; meses sem cobranças são preenchidos com zero. O período aceita até 120 meses inclusivos.

A consulta de resumo agrega os valores de `expense_installments.amount` pelo mês de vencimento e pela categoria em uma consulta ao banco. Assim, o total e os gráficos usam o mesmo recorte sem baixar cobranças em páginas sequenciais nem somar o preço total da compra em todos os meses.

Uma requisição parcelada pode usar, por exemplo, `"amount": "1200.00"`, `"amount_type": "total"`, `"payment_type": "installments"` e `"installment_count": 6`. A mesma compra pode usar `"amount": "200.00"` e `"amount_type": "installment"`.

O PUT continua atualizando o gasto inteiro. Mudanças no valor, nas datas ou na quantidade recalculam o cronograma; mudanças apenas na descrição, categoria ou meio de pagamento preservam as cobranças. DELETE remove o gasto e todas as cobranças. A documentação interativa fica em `/docs` enquanto o servidor está em execução.

## Testes

Instale as dependências de desenvolvimento e execute os testes a partir da pasta `backend`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

Os testes da API usam SQLite em memória; não criam, alteram ou removem dados do PostgreSQL local.
