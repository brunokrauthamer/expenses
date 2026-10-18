# Backend do Expenses

O backend usa FastAPI, SQLAlchemy, Alembic e PostgreSQL. Nesta etapa, ele contém somente a configuração de conexão e a migração inicial do banco.

## Organização

O projeto é um monólito modular. Cada domínio fica em `app/modules/` e separa:

- `model.py`: representação da tabela pelo SQLAlchemy;
- `schema.py`: contratos de entrada e saída da API;
- `service.py`: regras e consultas do domínio;
- `controller.py`: rotas HTTP do domínio.

Os módulos existentes são `categories` e `expenses`. O código técnico reutilizável fica em `app/shared/`; conexão e configuração ficam na raiz de `app/`.

## Configuração

1. Crie um banco PostgreSQL chamado `personal_expenses`.
2. Copie `.env.example` para `.env` e ajuste a variável `DATABASE_URL`.
3. Crie e ative um ambiente virtual Python.
4. Instale as dependências: `pip install -r requirements.txt`.
5. Aplique as migrações: `alembic upgrade head`.

As tabelas criadas são `categories` e `expenses`. A migração ainda não insere categorias iniciais, pois o pedido atual cobre somente a estrutura das tabelas.

## Testes

Instale as dependências de desenvolvimento e execute os testes a partir da pasta `backend`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

Os testes usam um banco SQLite temporário em memória. Eles não criam, alteram nem removem dados do PostgreSQL local.
